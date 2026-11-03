"""One production-only SMTP transport for every Django application email."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend


def real_email_allowed():
    return (
        settings.DJANGO_ENVIRONMENT == 'production' and settings.EMAIL_DELIVERY_ENABLED
    )


class ProductionEmailBackend(EmailBackend):
    def check_delivery(self):
        if not real_email_allowed():
            raise ImproperlyConfigured(
                'Real email delivery is restricted to explicitly enabled production.'
            )

    def open(self):
        self.check_delivery()
        return super().open()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        # Also guard a connection supplied or opened before settings changed.
        self.check_delivery()
        return super().send_messages(email_messages)
