"""Availability of transactional login email, shared by account workflows."""

from urllib.parse import urlsplit
from django.conf import settings
from eures_beta.emails.backend import real_email_allowed


def email_ready():
    origin = urlsplit(settings.LOGIN_EMAIL_ORIGIN)
    return bool(
        real_email_allowed()
        and settings.LOGIN_EMAIL_ENABLED
        and origin.scheme == 'https'
        and origin.hostname in settings.ALLOWED_HOSTS
        and not origin.username
        and not origin.password
        and origin.path in ('', '/')
        and not origin.query
        and not origin.fragment
        and settings.EMAIL_HOST
        and settings.DEFAULT_FROM_EMAIL
    )
