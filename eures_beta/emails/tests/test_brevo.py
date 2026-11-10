import json
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from eures_beta.users.views import email_ready


@override_settings(
    EMAIL_BACKEND='eures_beta.emails.brevo.BrevoEmailBackend',
    EMAIL_TRANSPORT='brevo',
    EMAIL_DELIVERY_ENABLED=True,
    LOGIN_EMAIL_ENABLED=True,
    LOGIN_EMAIL_ORIGIN='https://testserver',
    ALLOWED_HOSTS=['testserver'],
    EMAIL_HOST='',
    BREVO_API_KEY='fictional-api-key',
    BREVO_FROM_NAME='Match Europe',
    BREVO_REPLY_TO_EMAIL='reply@example.invalid',
    BREVO_REPLY_TO_NAME='Support',
    DEFAULT_FROM_EMAIL='sender@example.invalid',
)
class BrevoDeliveryTests(SimpleTestCase):
    @patch('eures_beta.emails.brevo.HTTPSConnection')
    def test_login_email_transport_is_ready_without_smtp_and_sends(self, https):
        self.assertTrue(email_ready())
        connection = https.return_value
        connection.getresponse.return_value.status = 201

        link = 'https://testserver.example/accounts/login/?a=1&b=2'
        body = render_to_string('users/login_email.txt', {'link': link})
        self.assertIn(link, body)
        self.assertEqual(
            send_mail('Connexion', body, None, ['user@example.invalid']), 1
        )

        https.assert_called_once_with('api.brevo.com', timeout=10)
        args, kwargs = connection.request.call_args
        self.assertEqual(args, ('POST', '/v3/smtp/email'))
        self.assertEqual(kwargs['headers']['api-key'], 'fictional-api-key')
        payload = json.loads(kwargs['body'])
        self.assertEqual(
            payload['sender'],
            {'email': 'sender@example.invalid', 'name': 'Match Europe'},
        )
        self.assertEqual(
            payload['replyTo'], {'email': 'reply@example.invalid', 'name': 'Support'}
        )
        self.assertEqual(payload['to'], [{'email': 'user@example.invalid'}])
        self.assertEqual(payload['textContent'], body)
        self.assertIn(
            'href="https://testserver.example/accounts/login/?a=1&amp;b=2"',
            payload['htmlContent'],
        )
        self.assertEqual(payload['headers']['X-Mailin-Track-Clicks'], 'false')
        connection.close.assert_called_once()

    @override_settings(BREVO_API_KEY='', EMAIL_HOST='smtp.example.invalid')
    @patch('eures_beta.emails.brevo.HTTPSConnection')
    def test_missing_key_does_not_fall_back_to_smtp(self, https):
        self.assertFalse(email_ready())
        with self.assertRaises(ImproperlyConfigured):
            send_mail('Connexion', 'Test', None, ['user@example.invalid'])
        https.assert_not_called()

    @override_settings(EMAIL_DELIVERY_ENABLED=False)
    @patch('eures_beta.emails.brevo.HTTPSConnection')
    def test_disabled_delivery_never_calls_brevo(self, https):
        self.assertFalse(email_ready())
        with self.assertRaises(ImproperlyConfigured):
            send_mail('Connexion', 'Test', None, ['user@example.invalid'])
        https.assert_not_called()

    @patch('eures_beta.emails.brevo.HTTPSConnection')
    def test_rejection_is_reported_without_reading_response_body(self, https):
        response = https.return_value.getresponse.return_value
        response.status = 403
        with self.assertRaisesRegex(OSError, 'HTTP 403'):
            send_mail('Connexion', 'Test', None, ['user@example.invalid'])
        response.read.assert_not_called()
        self.assertEqual(https.return_value.request.call_count, 1)

    @patch('eures_beta.emails.brevo.HTTPSConnection')
    def test_network_error_can_be_suppressed_without_retry(self, https):
        connection = https.return_value
        connection.request.side_effect = TimeoutError
        self.assertEqual(
            send_mail(
                'Connexion', 'Test', None, ['user@example.invalid'], fail_silently=True
            ),
            0,
        )
        connection.request.assert_called_once()
        connection.close.assert_called_once()
