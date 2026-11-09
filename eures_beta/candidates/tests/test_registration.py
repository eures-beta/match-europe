from datetime import timedelta
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates import registration
from eures_beta.candidates.journey import KEY
from eures_beta.candidates.models import CandidateProfile
from eures_beta.users.models import User


def answers():
    return dict(
        display_name='Fictional candidate',
        desired_occupations='Fictional job',
        desired_countries=['FR'],
        mobility='discuss',
        availability='discuss',
        contract_types=['discuss'],
        working_time=['discuss'],
        schedule_preference='discuss',
        working_conditions=['discuss'],
        salary_preference='discuss',
    )


@override_settings(DJANGO_ENVIRONMENT='preview', EMAIL_DELIVERY_ENABLED=False)
class CandidateRegistrationTests(TestCase):
    def pending(self, email='candidate@example.invalid'):
        return registration.create_request(email, 'fr')

    def open_link(self, user, client=None):
        client = client or self.client
        client.get(
            reverse('candidate_registration_confirm'),
            {'token': registration.token_for(user)},
            secure=True,
        )
        return client.get(reverse('candidate_registration_confirm'), secure=True)

    def confirm(self, client=None):
        return (client or self.client).post(
            reverse('candidate_registration_confirm'), secure=True
        )

    def test_email_precedes_questionnaire_and_public_outcomes_are_neutral(self):
        self.assertRedirects(
            self.client.get('/candidate/prepare/', secure=True),
            reverse('candidate_start'),
            fetch_redirect_response=False,
        )
        self.assertNotIn(KEY, self.client.session)
        existing = User.objects.create_user('employer@example.invalid', kind='employer')
        pages = []
        for email in ('new@example.invalid', existing.email):
            self.client.post(reverse('candidate_start'), {'email': email}, secure=True)
            response = self.client.get(
                reverse('candidate_registration_requested'), secure=True
            )
            pages.append(response.context['stage'])
            self.assertNotContains(response, email)
            self.assertNotContains(response, 'token=')
        self.assertEqual(pages, ['requested', 'requested'])
        existing.refresh_from_db()
        self.assertEqual(existing.kind, 'employer')

    def test_inactive_account_cannot_login_before_post_and_replay_fails(self):
        user = self.pending()
        token = registration.token_for(user)
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(CandidateProfile.objects.count(), 0)
        self.assertNotContains(self.open_link(user), token)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertRedirects(
            self.confirm(), reverse('candidate_prepare'), fetch_redirect_response=False
        )
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNone(user.candidate_verification_nonce)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.client.get(
            reverse('candidate_registration_confirm'), {'token': token}, secure=True
        )
        self.assertContains(self.confirm(), 'invalide')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CandidateProfile.objects.count(), 0)

    def test_expired_tampered_and_missing_tokens_do_not_activate(self):
        user = self.pending()
        token = registration.token_for(user)
        for invalid in ('', token + 'tampered', 'x' * 600):
            self.client.get(
                reverse('candidate_registration_confirm'),
                {'token': invalid},
                secure=True,
            )
            self.assertContains(self.confirm(), 'invalide')
        User.objects.filter(pk=user.pk).update(
            candidate_verification_expires=timezone.now() - timedelta(seconds=1)
        )
        self.open_link(user)
        self.assertContains(self.confirm(), 'invalide')
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_csrf_and_failed_activation_preserve_unconsumed_account(self):
        user = self.pending()
        client = Client(enforce_csrf_checks=True)
        self.open_link(user, client)
        self.assertEqual(self.confirm(client).status_code, 403)
        self.open_link(user)
        from django.core.exceptions import ValidationError

        with patch.object(User, 'save', side_effect=ValidationError('invalid')):
            self.assertContains(self.confirm(), 'invalide')
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.candidate_verification_nonce)

    def test_anonymous_repeat_does_not_modify_account_or_profile(self):
        user = self.pending()
        original = (
            user.candidate_verification_nonce,
            user.candidate_verification_expires,
        )
        self.assertEqual(
            registration.create_request(user.email.upper(), 'de').pk, user.pk
        )
        user.refresh_from_db()
        self.assertEqual(
            original,
            (user.candidate_verification_nonce, user.candidate_verification_expires),
        )
        user = registration.confirm_registration(registration.token_for(user))
        profile = registration.update_profile(user, answers(), 'fr')
        returned = registration.create_request(user.email, 'de')
        profile.refresh_from_db()
        self.assertEqual(returned.pk, user.pk)
        self.assertEqual(profile.display_name, 'Fictional candidate')
        self.assertEqual(profile.language, 'fr')
        with override_settings(DEBUG=True, ALLOWED_HOSTS=['127.0.0.1']):
            _, body = registration.confirmation_message(
                returned, 'http://127.0.0.1:9035'
            )
        self.assertIn('/accounts/confirm/?sesame=', body)

    def test_complete_questionnaire_creates_one_profile_and_edit_reuses_it(self):
        user = self.pending()
        self.open_link(user)
        self.confirm()
        self.client.get('/candidate/prepare/?lang=fr', secure=True)
        for step, data in (
            (1, {'desired_occupations': 'Fictional job', 'desired_countries': ['FR']}),
            (2, {'mobility': 'discuss'}),
            (
                3,
                {
                    k: v
                    for k, v in answers().items()
                    if k
                    in (
                        'availability',
                        'contract_types',
                        'working_time',
                        'schedule_preference',
                        'working_conditions',
                        'salary_preference',
                    )
                },
            ),
            (
                4,
                {
                    'display_name': 'Fictional candidate',
                    'contact_email': 'attacker@example.invalid',
                    'reviewed': 'on',
                },
            ),
        ):
            response = self.client.post(
                f'/candidate/prepare/?step={step}&lang=fr',
                {
                    'token': self.client.session[KEY]['token'],
                    'action': 'finish' if step == 4 else 'continue',
                    **data,
                },
                secure=True,
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('candidate_profile'))
        self.assertEqual(CandidateProfile.objects.count(), 1)
        self.assertNotIn(KEY, self.client.session)
        user.refresh_from_db()
        self.assertEqual(user.email, 'candidate@example.invalid')
        self.assertRedirects(
            self.client.get(reverse('candidate_start'), secure=True),
            reverse('candidate_profile'),
            fetch_redirect_response=False,
        )
        self.client.post(reverse('candidate_profile_edit'), secure=True)
        self.assertEqual(self.client.session[KEY]['owner_id'], user.pk)
        data = answers()
        data['display_name'] = 'Updated fictional name'
        registration.update_profile(user, data, 'en')
        self.assertEqual(CandidateProfile.objects.count(), 1)
        self.assertEqual(user.candidate_profile.display_name, 'Updated fictional name')

    def test_profile_private_wrong_role_and_account_switch_discard_old_draft(self):
        user = User.objects.create_user('owner@example.invalid', kind='candidate')
        registration.update_profile(user, answers(), 'fr')
        self.client.force_login(user)
        self.client.get('/candidate/prepare/', secure=True)
        first = self.client.session[KEY]['token']
        other = User.objects.create_user('other@example.invalid', kind='candidate')
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(reverse('candidate_profile'), secure=True).status_code, 404
        )
        self.client.get('/candidate/prepare/', secure=True)
        self.assertNotEqual(self.client.session[KEY]['token'], first)
        self.assertEqual(self.client.session[KEY]['data'], {})
        employer = User.objects.create_user('employer@example.invalid', kind='employer')
        self.client.force_login(employer)
        self.assertContains(
            self.client.get(reverse('candidate_start'), secure=True), 'autre rôle'
        )
        self.assertEqual(
            self.client.get(reverse('candidate_profile'), secure=True).status_code, 403
        )

    def test_operator_simulation_and_cleanup_only_unverified_expired_candidates(self):
        user = self.pending()
        with override_settings(DEBUG=True, ALLOWED_HOSTS=['127.0.0.1']):
            output = StringIO()
            call_command(
                'candidate_email',
                user.email,
                origin='http://127.0.0.1:9035',
                stdout=output,
            )
            self.assertIn('/candidate/registration/confirm/?token=', output.getvalue())
        User.objects.filter(pk=user.pk).update(
            candidate_verification_expires=timezone.now() - timedelta(seconds=1)
        )
        active = User.objects.create_user('active@example.invalid', kind='candidate')
        disabled = User.objects.create_user(
            'disabled@example.invalid', kind='candidate', is_active=False
        )
        call_command('cleanup_candidate_registrations', stdout=StringIO())
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        call_command('cleanup_candidate_registrations', apply=True, stdout=StringIO())
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertTrue(
            User.objects.filter(pk__in=[active.pk, disabled.pk]).count() == 2
        )

    def test_expired_pending_link_can_be_renewed_without_reactivating_disabled_accounts(
        self,
    ):
        user = self.pending()
        old = registration.token_for(user)
        User.objects.filter(pk=user.pk).update(
            candidate_verification_expires=timezone.now() - timedelta(seconds=1)
        )
        renewed = registration.create_request(user.email, 'de')
        self.assertNotEqual(
            user.candidate_verification_nonce, renewed.candidate_verification_nonce
        )
        self.assertIsNone(registration.find_registration(old))
        self.assertFalse(renewed.is_active)
        disabled = User.objects.create_user(
            'disabled@example.invalid', kind='candidate', is_active=False
        )
        self.assertIsNone(registration.create_request(disabled.email, 'fr'))

    def test_production_uses_shared_backend_and_admin_hides_nonce(self):
        user = self.pending()
        from django.core import mail
        from django.contrib import admin
        from django.test import RequestFactory

        with override_settings(
            DJANGO_ENVIRONMENT='production',
            EMAIL_DELIVERY_ENABLED=True,
            LOGIN_EMAIL_ENABLED=True,
            LOGIN_EMAIL_ORIGIN='https://testserver',
            ALLOWED_HOSTS=['testserver'],
            EMAIL_HOST='smtp.example.invalid',
            DEFAULT_FROM_EMAIL='noreply@example.invalid',
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ):
            self.assertTrue(registration.send_confirmation(user))
            self.assertEqual(mail.outbox[-1].to, [user.email])
            self.assertIn(
                '/candidate/registration/confirm/?token=', mail.outbox[-1].body
            )
        request = RequestFactory().get('/')
        request.user = User.objects.create_superuser(
            'staff@example.invalid', kind='adviser'
        )
        self.assertNotIn(
            'candidate_verification_nonce',
            admin.site._registry[User].get_fields(request, user),
        )

    def test_confirmation_delivery_remains_disabled_in_preview(self):
        user = self.pending()
        with patch('eures_beta.candidates.registration.send_mail') as send:
            self.assertFalse(registration.send_confirmation(user))
        send.assert_not_called()


class CandidateConfirmationConcurrencyTests(TransactionTestCase):
    def test_two_confirmations_activate_exactly_once(self):
        user = registration.create_request('concurrent@example.invalid', 'fr')
        token = registration.token_for(user)
        barrier = Barrier(2)

        def confirm():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return bool(registration.confirm_registration(token))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: confirm(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CandidateProfile.objects.count(), 0)
