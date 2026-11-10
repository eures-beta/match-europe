"""One explicitly configured SMTP transport for every application email."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend


def real_email_allowed():
    return settings.EMAIL_DELIVERY_ENABLED


def email_transport_ready():
    credential = (
        settings.BREVO_API_KEY
        if settings.EMAIL_TRANSPORT == 'brevo'
        else settings.EMAIL_HOST
    )
    return bool(
        real_email_allowed() and credential.strip() and settings.DEFAULT_FROM_EMAIL
    )


def check_delivery():
    if not real_email_allowed():
        raise ImproperlyConfigured(
            'Real email delivery requires explicit configuration.'
        )


class ProductionEmailBackend(EmailBackend):
    def open(self):
        check_delivery()
        return super().open()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        # Also guard a connection supplied or opened before settings changed.
        check_delivery()
        return super().send_messages(email_messages)
