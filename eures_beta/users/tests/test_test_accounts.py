import json
import os
import subprocess
import sys
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.employers.models import (
    Company,
    JobOffer,
    CompanyMembership,
)
from eures_beta.users.test_accounts import ACCOUNTS, prepared_user

User = get_user_model()


@override_settings(
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='preview',
    EMAIL_DELIVERY_ENABLED=False,
)
class TestAccountAccessTests(TestCase):
    def seed(self):
        call_command('seed_test_accounts', stdout=StringIO())

    def test_pages_do_not_seed_data_implicitly(self):
        page = self.client.get(reverse('test_accounts'))
        self.assertEqual(page.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertIn('no-store', page['Cache-Control'])

    @override_settings(
        DJANGO_ENVIRONMENT='preview', MATCHING_ENABLED=True, LOGIN_EMAIL_ENABLED=False
    )
    def test_preview_candidates_are_ready_for_adviser_review(self):
        from eures_beta.users.adviser_matching import pending_pairs
        from eures_beta.matching.models import CandidateOfferReview

        self.seed()
        self.seed()
        self.assertEqual(CandidateOfferReview.objects.count(), 1)
        for key in ('candidate-pwa', 'candidate-pwa-replay'):
            client = Client()
            response = client.post(
                reverse('test_account_sign_in'), {'account': key}, follow=True
            )
            self.assertEqual(response.request['PATH_INFO'], '/candidate/profile/')
            user = prepared_user(key)
            self.assertEqual(client.session['_auth_user_id'], str(user.pk))
            if key == 'candidate-pwa-replay':
                from eures_beta.matching.confirmation_services import review

                confirmation = ConfirmationRequest.objects.get(
                    pair__candidate__user=user
                )
                self.assertIsNone(review(confirmation)['pending'])
            else:
                self.assertTrue(pending_pairs().filter(candidate__user=user).exists())
            self.assertContains(response, 'data-preview-push')

    @override_settings(
        MATCHING_ENABLED=True,
        LOGIN_EMAIL_ENABLED=False,
        CONFIRMATION_DIALOGUE_SIMULATED=True,
    )
    def test_preview_push_starts_only_after_adviser_validation(self):
        import base64
        from unittest.mock import patch

        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from eures_beta.matching.models import CandidateOfferReview
        from eures_beta.users.adviser_matching import pending_pairs

        self.seed()
        user = prepared_user('candidate-pwa')
        pair = pending_pairs().get(candidate__user=user)
        adviser = Client()
        adviser.force_login(prepared_user('adviser'))
        detail = reverse('adviser_match', args=[pair.pk])
        decision = {'action': 'retained', 'evaluation': pair.evaluation_id}

        candidate = Client()
        candidate.force_login(user)
        point = (
            ec.generate_private_key(ec.SECP256R1())
            .public_key()
            .public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        )
        payload = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/fictional',
            'keys': {
                'p256dh': base64.urlsafe_b64encode(point).decode(),
                'auth': base64.urlsafe_b64encode(bytes(16)).decode(),
            },
        }
        subscription = reverse('candidate_push_subscriptions')
        self.assertEqual(
            candidate.post(
                subscription,
                {**payload, 'endpoint': 'https://localhost/'},
                content_type='application/json',
            ).status_code,
            400,
        )
        self.assertEqual(
            candidate.post(
                subscription, payload, content_type='application/json'
            ).status_code,
            200,
        )
        with patch('pywebpush.webpush') as send:
            send.return_value.status_code = 201
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(adviser.post(detail, decision).status_code, 302)
                send.assert_not_called()
            send.assert_called_once()
        confirmation = CandidateOfferReview.objects.get(pair=pair)
        dialogue = reverse('candidate_offer_dialogue', args=[confirmation.pk])
        payload = json.loads(send.call_args.kwargs['data'])
        self.assertTrue(payload['body'])
        self.assertEqual(payload['url'], dialogue)
        page = candidate.get(payload['url'])
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['current']['kind'], 'schedule')
        follow = reverse('adviser_conversation', args=[confirmation.pk])
        with patch(
            'eures_beta.candidates.preview_push.notify', return_value=True
        ) as resend:
            self.assertEqual(
                adviser.post(follow, {'action': 'resend'}).status_code, 200
            )
            self.assertEqual(
                adviser.post(follow, {'action': 'resend'}).status_code, 429
            )
            resend.assert_called_once_with(confirmation)

    @override_settings(MATCHING_ENABLED=True, CONFIRMATION_DIALOGUE_SIMULATED=True)
    def test_push_is_universal_and_subscription_is_optional(self):
        from unittest.mock import patch
        from eures_beta.candidates import preview_push
        from eures_beta.matching.models import CandidateOfferReview
        from eures_beta.users.adviser_matching import pending_pairs, record_review

        self.seed()
        user = prepared_user("candidate-pwa")
        user.email = "candidate@example.org"
        user.save(update_fields=["email"])
        adviser = prepared_user("adviser")
        pair = pending_pairs().get(candidate__user=user)
        with patch.object(preview_push, "notify") as notify:
            for environment in ("local", "preview", "production"):
                with (
                    self.subTest(environment=environment),
                    self.settings(
                        DJANGO_ENVIRONMENT=environment, TEST_ACCOUNTS_ENABLED=False
                    ),
                ):
                    self.assertTrue(preview_push.available())
                    self.client.force_login(user)
                    page = self.client.get(reverse("candidate_profile"))
                    self.assertContains(page, reverse("candidate_push_subscriptions"))
            with self.captureOnCommitCallbacks(execute=True):
                record_review(adviser, pair, pair.evaluation_id, "retained")
                notify.assert_not_called()
            notify.assert_called_once_with(CandidateOfferReview.objects.get(pair=pair))

    @override_settings(DJANGO_ENVIRONMENT='local')
    def test_seed_is_idempotent_and_preserves_edits(self):
        self.seed()
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(CompanyMembership.objects.count(), 1)
        self.assertEqual(JobOffer.objects.count(), 2)
        identities = list(User.objects.order_by('pk').values_list('pk', flat=True))
        offer = JobOffer.objects.first()
        offer.data = {'description': 'An edit that must survive redeployment'}
        offer.save()
        self.seed()
        self.assertEqual(
            list(User.objects.order_by('pk').values_list('pk', flat=True)), identities
        )
        self.assertEqual(JobOffer.objects.count(), 2)
        offer.refresh_from_db()
        self.assertEqual(
            offer.data, {'description': 'An edit that must survive redeployment'}
        )
        for key in ACCOUNTS:
            user = prepared_user(key)
            self.assertIsNotNone(user)
            self.assertFalse(user.has_usable_password())

    def test_seeding_refuses_real_addresses_before_creating_any_fixture(self):
        user = User.objects.create_user(email='someone@example.org', kind='adviser')
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(list(User.objects.all()), [user])
        self.assertFalse(JobOffer.objects.exists())
        self.assertEqual(self.client.get(reverse('test_accounts')).status_code, 404)
        response = self.client.post(
            reverse('test_account_sign_in'), {'account': 'admin'}
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_collision_is_not_overwritten_or_promoted(self):
        user = User.objects.create_user(
            email=ACCOUNTS['admin']['email'], kind='employer'
        )
        with self.assertRaises(CommandError):
            self.seed()
        user.refresh_from_db()
        self.assertEqual(user.kind, 'employer')
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(User.objects.count(), 1)

    def test_each_fixed_role_signs_in_without_email_or_password(self):
        self.seed()
        for key in ACCOUNTS:
            client = Client()
            response = client.post(
                reverse('test_account_sign_in'),
                {'account': key, 'next': 'https://attacker.invalid'},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)
            user = prepared_user(key)
            self.assertEqual(client.session['_auth_user_id'], str(user.pk))
            self.assertEqual(client.session.get_expiry_age(), 30 * 86400)
            self.assertEqual(
                response.request['PATH_INFO'],
                '/admin/' if key == 'admin' else '/accounts/dashboard/',
            )
            self.assertEqual(
                client.get('/admin/').status_code, 200 if key == 'admin' else 302
            )
        self.assertEqual(len(mail.outbox), 0)

    def test_unlisted_or_modified_accounts_cannot_be_selected(self):
        self.seed()
        for selection in ('unknown', 'operator@example.org', '', '1'):
            self.assertEqual(
                self.client.post(
                    reverse('test_account_sign_in'), {'account': selection}
                ).status_code,
                404,
            )
        user = prepared_user('adviser')
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        self.assertEqual(
            self.client.post(
                reverse('test_account_sign_in'), {'account': 'adviser'}
            ).status_code,
            404,
        )
        page = self.client.get(reverse('test_accounts'))
        self.assertNotContains(page, ACCOUNTS['adviser']['email'])
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_or_password_enabled_fixture_cannot_be_used(self):
        self.seed()
        user = prepared_user('admin')
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(
            self.client.post(
                reverse('test_account_sign_in'), {'account': 'admin'}
            ).status_code,
            404,
        )
        user.is_active = True
        user.set_password('fictional-test-password')
        user.save()
        self.assertEqual(
            self.client.post(
                reverse('test_account_sign_in'), {'account': 'admin'}
            ).status_code,
            404,
        )

    def test_get_cannot_sign_in_and_post_requires_csrf(self):
        self.seed()
        self.assertEqual(
            self.client.get(reverse('test_account_sign_in')).status_code, 405
        )
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                reverse('test_account_sign_in'), {'account': 'admin'}
            ).status_code,
            403,
        )
        client.get(reverse('test_accounts'), secure=True)
        response = client.post(
            reverse('test_account_sign_in'),
            {
                'account': 'adviser',
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
            },
            secure=True,
            HTTP_ORIGIN='https://testserver',
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            client.session['_auth_user_id'], str(prepared_user('adviser').pk)
        )

    def test_switching_account_rotates_session_and_preserves_selected_language(self):
        self.seed()
        self.client.post(reverse('test_account_sign_in'), {'account': 'admin'})
        previous = self.client.session.session_key
        response = self.client.post(
            reverse('test_account_sign_in') + '?lang=fr',
            {'account': 'employer'},
            follow=True,
        )
        self.assertNotEqual(self.client.session.session_key, previous)
        self.assertEqual(self.client.session['login_language'], 'fr')
        self.assertContains(response, '<html lang="fr">')
        self.assertEqual(response.request['PATH_INFO'], '/accounts/dashboard/')

    def test_banner_is_present_on_public_and_admin_pages_in_all_languages(self):
        self.seed()
        for language, label in (
            ('fr', 'Choisir un compte de test'),
            ('en', 'Choose a test account'),
            ('de', 'Testkonto auswählen'),
        ):
            page = self.client.get(reverse('test_accounts'), {'lang': language})
            self.assertContains(page, label)
            self.assertContains(page, '?lang=' + language)
        self.assertContains(self.client.get('/'), 'test-accounts-banner')
        self.client.post(reverse('test_account_sign_in'), {'account': 'admin'})
        self.assertContains(self.client.get('/admin/'), 'test-accounts-banner')

    def test_production_disabled_unknown_and_email_enabled_environments_are_closed(
        self,
    ):
        for environment, enabled, email_enabled in (
            ('production', True, False),
            ('production', False, False),
            ('unknown', True, False),
            ('preview', False, False),
            ('preview', True, True),
        ):
            with (
                self.subTest(
                    environment=environment, enabled=enabled, email=email_enabled
                ),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    TEST_ACCOUNTS_ENABLED=enabled,
                    EMAIL_DELIVERY_ENABLED=email_enabled,
                ),
            ):
                self.assertEqual(
                    self.client.get(reverse('test_accounts')).status_code, 404
                )
                self.assertEqual(
                    self.client.post(
                        reverse('test_account_sign_in'), {'account': 'admin'}
                    ).status_code,
                    404,
                )
                self.assertNotContains(
                    self.client.get('/'), 'class="test-accounts-banner"'
                )
                with self.assertRaises(CommandError):
                    self.seed()
        self.assertFalse(User.objects.exists())

    def test_invalid_startup_configuration_fails_before_serving_requests(self):
        for environment, delivery in (
            ('production', '0'),
            ('unknown', '0'),
            ('preview', '1'),
        ):
            result = subprocess.run(
                [sys.executable, '-c', 'import config.settings'],
                env={
                    **os.environ,
                    'DJANGO_ENVIRONMENT': environment,
                    'TEST_ACCOUNTS_ENABLED': '1',
                    'EMAIL_DELIVERY_ENABLED': delivery,
                    'DJANGO_SECRET_KEY': 'fictional-key',
                },
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Test accounts require', result.stderr)
