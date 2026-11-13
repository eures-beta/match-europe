from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.mail import EmailMessage
from django.core.mail.backends.filebased import EmailBackend
from django.test import SimpleTestCase

from .journeys import Browser


class CapturedEmailTests(SimpleTestCase):
    def test_confirmation_reads_each_message_when_django_reuses_a_mail_file(self):
        with TemporaryDirectory() as directory:
            artifacts = Path(directory)
            mail = artifacts / 'mail'
            connection = EmailBackend(file_path=str(mail))
            connection.send_messages(
                [
                    EmailMessage(
                        'Earlier message',
                        'Unrelated content',
                        'sender@example.invalid',
                        ['adviser@example.invalid'],
                    ),
                    EmailMessage(
                        'Invitation',
                        'https://web:8443/accounts/invitations/confirm/?invitation=fictional',
                        'sender@example.invalid',
                        ['invited@example.invalid'],
                    ),
                ]
            )
            self.assertEqual(len(list(mail.glob('*'))), 1)
            browser = object.__new__(Browser)
            browser.request = Mock()
            with patch('eures_beta.e2e.journeys.ARTIFACTS', artifacts):
                browser.confirm_mail(
                    'invited@example.invalid', '/accounts/invitations/confirm/'
                )
            self.assertEqual(browser.request.call_count, 2)
            browser.request.assert_any_call(
                '/accounts/invitations/confirm/?invitation=fictional'
            )
            browser.request.assert_any_call('/accounts/invitations/confirm/', {})
