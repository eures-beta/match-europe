"""Never contact SMTP from local development or disposable previews."""

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, send_mail
from django.test import SimpleTestCase, override_settings

from eures_beta.users.email_backend import ProductionEmailBackend
from eures_beta.users.views import email_ready


@override_settings(
    EMAIL_BACKEND='eures_beta.users.email_backend.ProductionEmailBackend',
    EMAIL_DELIVERY_ENABLED=True,
    LOGIN_EMAIL_ENABLED=True,
    LOGIN_EMAIL_ORIGIN='https://testserver',
    ALLOWED_HOSTS=['testserver'],
    EMAIL_HOST='smtp.example.invalid',
    EMAIL_HOST_USER='fictional',
    EMAIL_HOST_PASSWORD='fictional',
    DEFAULT_FROM_EMAIL='test@example.invalid',
)
class EmailDeliveryTests(SimpleTestCase):
    def test_nonproduction_never_opens_smtp_even_with_credentials(self):
        for environment in ('local', 'development', 'preview', '', 'unknown'):
            with (
                self.subTest(environment=environment),
                override_settings(DJANGO_ENVIRONMENT=environment),
                patch('django.core.mail.backends.smtp.EmailBackend.open') as smtp,
            ):
                self.assertFalse(email_ready())
                with self.assertRaises(ImproperlyConfigured):
                    send_mail('Test', 'Fictional', None, ['test@example.invalid'])
                with self.assertRaises(ImproperlyConfigured):
                    ProductionEmailBackend(fail_silently=True).open()
                smtp.assert_not_called()

    @override_settings(DJANGO_ENVIRONMENT='production', EMAIL_DELIVERY_ENABLED=False)
    def test_production_requires_explicit_opt_in(self):
        self.assertFalse(email_ready())
        with patch('django.core.mail.backends.smtp.EmailBackend.open') as smtp:
            with self.assertRaises(ImproperlyConfigured):
                send_mail('Test', 'Fictional', None, ['test@example.invalid'])
            smtp.assert_not_called()

    @override_settings(DJANGO_ENVIRONMENT='preview')
    def test_preexisting_connection_cannot_bypass_policy(self):
        backend = ProductionEmailBackend()
        backend.connection = object()
        with patch('django.core.mail.backends.smtp.EmailBackend.send_messages') as smtp:
            with self.assertRaises(ImproperlyConfigured):
                EmailMessage(
                    'Test', 'Fictional', to=['test@example.invalid'], connection=backend
                ).send()
            smtp.assert_not_called()

    @override_settings(DJANGO_ENVIRONMENT='production')
    def test_enabled_production_uses_django_smtp(self):
        self.assertTrue(email_ready())
        with patch(
            'django.core.mail.backends.smtp.EmailBackend.send_messages', return_value=1
        ) as smtp:
            self.assertEqual(
                send_mail('Test', 'Fictional', None, ['test@example.invalid']), 1
            )
            smtp.assert_called_once()
