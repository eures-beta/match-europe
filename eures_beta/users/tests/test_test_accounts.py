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
                    SHARED_DEMO=True,
                    DEMO_MODE=True,
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
