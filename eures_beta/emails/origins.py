"""Validate public email-link origins without coupling authentication to invitations."""

from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_origin(origin):
    parsed = urlsplit(origin)
    local = (
        settings.DEBUG
        and parsed.scheme == 'http'
        and parsed.hostname in ('localhost', '127.0.0.1', '[::1]')
    )
    if (
        not (parsed.scheme == 'https' or local)
        or parsed.hostname not in settings.ALLOWED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ('', '/')
    ):
        raise ValidationError(
            'Use an allowed HTTPS origin (HTTP loopback only in DEBUG).'
        )
    return origin.rstrip('/')
