"""Optional Brevo API transport for transactional application emails."""

import json
from email.utils import parseaddr
from http.client import HTTPException, HTTPSConnection

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import urlize

from .backend import check_delivery, email_transport_ready


def address(value, fallback_name=''):
    name, email = parseaddr(value)
    return (
        {'email': email, 'name': name or fallback_name}
        if name or fallback_name
        else {'email': email}
    )


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        check_delivery()
        if not email_transport_ready():
            raise ImproperlyConfigured(
                'Brevo requires an API key and a sender address.'
            )

        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                self.send_message(message)
            except (OSError, ValueError):
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent

    def send_message(self, message):
        if (
            not message.to
            or message.attachments
            or getattr(message, 'alternatives', ())
            or message.extra_headers
            or message.content_subtype != 'plain'
            or len(message.reply_to) > 1
        ):
            raise ValueError('Unsupported email format for the Brevo API transport.')

        payload = {
            'sender': address(message.from_email, settings.BREVO_FROM_NAME),
            'to': [address(value) for value in message.to],
            'subject': message.subject,
            'textContent': message.body,
            'htmlContent': '<html><body><pre>'
            + urlize(message.body, autoescape=True)
            + '</pre></body></html>',
            'headers': {
                'X-Mailin-Track': 'false',
                'X-Mailin-Track-Clicks': 'false',
                'X-Mailin-Track-Opens': 'false',
            },
        }
        for field in ('cc', 'bcc'):
            if recipients := getattr(message, field):
                payload[field] = [address(value) for value in recipients]
        if message.reply_to:
            payload['replyTo'] = address(message.reply_to[0])
        elif settings.BREVO_REPLY_TO_EMAIL:
            payload['replyTo'] = address(
                settings.BREVO_REPLY_TO_EMAIL, settings.BREVO_REPLY_TO_NAME
            )

        connection = HTTPSConnection('api.brevo.com', timeout=settings.EMAIL_TIMEOUT)
        try:
            connection.request(
                'POST',
                '/v3/smtp/email',
                body=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'api-key': settings.BREVO_API_KEY.strip(),
                },
            )
            status = connection.getresponse().status
        except (OSError, HTTPException, ValueError):
            raise OSError('Brevo email transport failed.') from None
        finally:
            connection.close()
        if status != 201:
            raise OSError(f'Brevo email transport returned HTTP {status}.')
