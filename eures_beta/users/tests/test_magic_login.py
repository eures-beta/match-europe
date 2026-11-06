import logging
import re
import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from sesame.utils import get_token, get_user

from eures_beta.logging import RedactAccessLinks
from eures_beta.users.models import LoginRateLimit


@patch.dict('os.environ', {'ME_EMPLOYER_DEV_ACCESS': '1'})
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.example.invalid',
    DEFAULT_FROM_EMAIL='no-reply@example.invalid',
    LOGIN_EMAIL_ORIGIN='https://testserver',
    LOGIN_EMAIL_ENABLED=True,
    DJANGO_ENVIRONMENT='production',
    EMAIL_DELIVERY_ENABLED=True,
)
class MagicLoginTests(TestCase):
    def test_https_browser_can_confirm_without_disabling_csrf_or_leaking_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(
            '/accounts/confirm/?sesame=' + get_token(self.user), secure=True
        )
        # The token-bearing redirect must not disclose the secret as a referrer.
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        clean = client.get(response.url, secure=True)
        # A no-referrer document makes Chromium submit Origin: null. Django
        # correctly rejects that POST, even with a valid CSRF cookie and field.
        # same-origin keeps HTTPS CSRF verification while hiding off-site referrers.
        self.assertEqual(clean['Referrer-Policy'], 'same-origin')
        self.assertNotContains(clean, 'sesame=')
        csrf = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', clean.content.decode()
        )[1]
        rejected = client.post(
            '/accounts/confirm/',
            {'csrfmiddlewaretoken': csrf},
            secure=True,
            HTTP_ORIGIN='https://attacker.invalid',
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertNotIn('_auth_user_id', client.session)
        accepted = client.post(
            '/accounts/confirm/',
            {'csrfmiddlewaretoken': csrf},
            secure=True,
            HTTP_ORIGIN='https://testserver',
            HTTP_REFERER='https://testserver/accounts/confirm/',
        )
        self.assertRedirects(accepted, '/accounts/dashboard/')
        self.assertEqual(client.session['_auth_user_id'], str(self.user.pk))

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='invited@example.invalid', kind='adviser'
        )

    def request_link(self, client=None, email=None):
        client = client or self.client
        client.post('/accounts/login/?lang=en', {'email': email or self.user.email})
        url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith('https://')
        )
        return urlsplit(url).path + '?' + urlsplit(url).query

    def test_login_in_common_header_in_all_languages(self):
        for lang, label in [
            ('fr', 'Se connecter'),
            ('en', 'Sign in'),
            ('de', 'Anmelden'),
        ]:
            for path in [
                '/',
                '/candidate/',
                '/project/',
                '/journal/',
                '/statistics/',
                f'/employer/pages/{lang}.html',
                f'/employer/pages/import-{lang}.html',
                f'/employer/pages/privacy-{lang}.html',
            ]:
                with self.subTest(path=path, lang=lang):
                    response = self.client.get(path, {'lang': lang})
                    self.assertContains(response, '/accounts/login/?lang=' + lang)
                    self.assertContains(response, label)
        response = self.client.get('/accounts/login/?lang=en')
        self.assertContains(
            response, 'Employer accounts are created by our Match Europe advisers.'
        )
        self.assertContains(
            response,
            'href="mailto:eric.barthelemy@francetravail.fr"',
        )
        self.assertNotContains(response, 'type="password"')

    def test_no_signup_or_account_enumeration(self):
        count = get_user_model().objects.count()
        known = self.client.post('/accounts/login/', {'email': self.user.email})
        unknown = Client().post(
            '/accounts/login/', {'email': 'unknown@example.invalid', 'kind': 'employer'}
        )
        inactive = get_user_model().objects.create_user(
            email='inactive@example.invalid', kind='employer', is_active=False
        )
        blocked = Client().post('/accounts/login/', {'email': inactive.email})
        self.assertEqual(known.context['stage'], unknown.context['stage'])
        self.assertEqual(blocked.context['stage'], known.context['stage'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(get_user_model().objects.count(), count + 1)

    def test_existing_employer_and_adviser_can_login_but_not_new_addresses(self):
        for kind in ('adviser', 'employer'):
            user = get_user_model().objects.create_user(
                email=kind + '@example.invalid', kind=kind
            )
            client = Client()
            link = self.request_link(client, user.email.upper())
            self.assertRedirects(client.get(link), '/accounts/confirm/')
            self.assertNotIn('_auth_user_id', client.session)
            self.assertRedirects(
                client.post('/accounts/confirm/'), '/accounts/dashboard/'
            )
            self.assertEqual(str(user.pk), client.session['_auth_user_id'])

    def test_get_and_mail_scanner_do_not_consume_token_and_url_is_cleaned(self):
        link = self.request_link()
        response = self.client.get(link)
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertNotIn('sesame', response.url)
        self.assertIsNone(get_user_model().objects.get(pk=self.user.pk).last_login)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(self.client.get(response.url), 'Confirm')
        self.assertRedirects(self.client.post(response.url), '/accounts/dashboard/')

    def test_tokens_are_single_use_even_in_another_browser(self):
        link = self.request_link()
        first, second = Client(), Client()
        first.get(link)
        second.get(link)
        first.post('/accounts/confirm/')
        response = second.post('/accounts/confirm/')
        self.assertEqual(response.context['stage'], 'invalid')
        self.assertNotIn('_auth_user_id', second.session)

    def test_expired_tampered_inactive_and_email_changed_tokens_are_rejected(self):
        token = get_token(self.user)
        with patch('sesame.tokens_v2.time.time', return_value=time.time() + 3601):
            self.assertIsNone(get_user(token, update_last_login=False))
        self.assertIsNone(get_user(token + 'tampered', update_last_login=False))
        self.user.email = 'changed@example.invalid'
        self.user.save()
        self.assertIsNone(get_user(token, update_last_login=False))
        token = get_token(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(get_user(token, update_last_login=False))

    def test_deleted_account_is_never_recreated(self):
        link = self.request_link()
        self.client.get(link)
        self.user.delete()
        self.assertEqual(
            self.client.post('/accounts/confirm/').context['stage'], 'invalid'
        )
        self.assertFalse(get_user_model().objects.exists())

    def test_rate_limit_is_shared_between_browsers_and_does_not_reveal_account(self):
        for _ in range(7):
            response = Client().post('/accounts/login/', {'email': self.user.email})
            self.assertEqual(response.context['stage'], 'sent')
        self.assertEqual(len(mail.outbox), 5)
        self.assertFalse(
            LoginRateLimit.objects.filter(key__contains='invited').exists()
        )
        LoginRateLimit.objects.update(expires=timezone.now() - timedelta(seconds=1))
        self.client.post('/accounts/login/', {'email': self.user.email})
        self.assertEqual(len(mail.outbox), 6)

    def test_ip_limit_covers_unknown_addresses_and_cannot_be_bypassed_with_forwarded_header(
        self,
    ):
        for i in range(30):
            Client().post('/accounts/login/', {'email': f'unknown{i}@example.invalid'})
        self.client.post(
            '/accounts/login/',
            {'email': self.user.email},
            HTTP_X_FORWARDED_FOR='192.0.2.1',
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_no_host_header_or_next_parameter_is_used_in_email_or_redirect(self):
        response = self.client.post(
            '/accounts/login/?next=https://evil.invalid', {'email': self.user.email}
        )
        self.assertEqual(response.context['stage'], 'sent')
        self.assertNotIn('evil.invalid', mail.outbox[-1].body)
        self.assertIn('https://testserver/accounts/confirm/', mail.outbox[-1].body)

    def test_unconfigured_delivery_is_explicit_and_never_exposes_a_link(self):
        with override_settings(LOGIN_EMAIL_ENABLED=False):
            response = self.client.post(
                '/accounts/login/?lang=en', {'email': self.user.email}
            )
            self.assertContains(response, 'Email delivery is not available yet')
            self.assertContains(response, 'disabled')
            self.assertNotContains(response, 'sesame=')
            self.assertNotIn('magic_login_token', self.client.session)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_delivery_failure_does_not_log_secrets_or_reveal_existing_accounts(
        self,
    ):
        with patch(
            'eures_beta.users.views.send_mail',
            side_effect=RuntimeError('sensitive payload'),
        ):
            with self.assertLogs('eures_beta.users.views', level='ERROR') as logs:
                response = self.client.post(
                    '/accounts/login/', {'email': self.user.email}
                )
        self.assertEqual(response.context['stage'], 'sent')
        self.assertNotIn('sensitive payload', str(logs.output))
        self.assertNotIn(self.user.email, str(logs.output))

    def test_login_request_confirmation_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for path in ('/accounts/login/', '/accounts/confirm/', '/accounts/logout/'):
            self.assertEqual(
                client.post(path, {'email': self.user.email}).status_code, 403
            )
        self.assertEqual(client.get('/accounts/logout/').status_code, 405)

    def test_password_backend_and_password_admin_endpoints_are_disabled(self):
        self.user.set_password('fictional-password')
        self.user.save()
        self.assertIsNone(
            authenticate(username=self.user.email, password='fictional-password')
        )
        self.assertIsNone(
            authenticate(email=self.user.email, password='fictional-password')
        )
        self.assertRedirects(self.client.get('/admin/login/'), '/accounts/login/')
        self.assertEqual(self.client.get('/admin/password_change/').status_code, 404)
        self.assertEqual(self.client.get('/accounts/password/reset/').status_code, 404)

    def test_session_expires_after_30_days_and_activity_extends_expiry(self):
        link = self.request_link()
        self.client.get(link)
        self.client.post('/accounts/confirm/')
        key = self.client.session.session_key
        before = Session.objects.get(session_key=key).expire_date
        now = timezone.now() + timedelta(days=2)
        with patch(
            'django.contrib.sessions.backends.base.timezone.now', return_value=now
        ):
            response = self.client.get('/')
        after = Session.objects.get(session_key=key).expire_date
        self.assertGreater(after, before + timedelta(days=1))
        self.assertEqual(
            int(response.cookies[settings.SESSION_COOKIE_NAME]['max-age']), 30 * 86400
        )
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        self.assertFalse(self.client.get('/').wsgi_request.user.is_authenticated)

    def test_token_is_redacted_from_application_access_logs(self):
        record = logging.LogRecord(
            'django.server',
            logging.INFO,
            '',
            0,
            'GET /accounts/confirm/?sesame=secret&lang=fr',
            (),
            None,
        )
        RedactAccessLinks().filter(record)
        self.assertNotIn('secret', record.getMessage())

    def test_validation_and_email_follow_the_selected_language(self):
        for language, error, subject in (
            (
                'fr',
                'Saisissez une adresse email valide.',
                'Votre lien de connexion Match Europe',
            ),
            ('en', 'Enter a valid email address.', 'Your Match Europe sign-in link'),
            (
                'de',
                'Geben Sie eine gültige E-Mail-Adresse ein.',
                'Ihr Anmeldelink für Match Europe',
            ),
        ):
            response = self.client.post(
                '/accounts/login/?lang=' + language, {'email': 'invalid'}
            )
            self.assertContains(response, error)
            self.client.post(
                '/accounts/login/?lang=' + language, {'email': self.user.email}
            )
            self.assertEqual(mail.outbox[-1].subject, subject)

    def test_read_only_admin_cannot_create_accounts_or_set_passwords(self):
        staff = get_user_model().objects.create_superuser(
            email='staff@example.invalid', kind='adviser'
        )
        self.client.force_login(staff)
        response = self.client.get('/admin/users/user/add/')
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            '/admin/users/user/add/',
            {
                'email': 'invited-adviser@example.invalid',
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            get_user_model()
            .objects.filter(email='invited-adviser@example.invalid')
            .exists()
        )
        user = self.user
        self.assertFalse(user.has_usable_password())
        # ModelAdmin has no password-change route; its catch-all treats it as an ID.
        password_url = f'/admin/users/user/{user.pk}/password/'
        self.assertRedirects(
            self.client.get(password_url),
            password_url + 'change/',
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.post(
                password_url,
                {
                    'password1': 'ShouldNotBeSaved123!',
                    'password2': 'ShouldNotBeSaved123!',
                },
            ),
            password_url + 'change/',
            fetch_redirect_response=False,
        )
        self.assertNotContains(
            self.client.get(password_url, follow=True), 'type="password"'
        )
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
