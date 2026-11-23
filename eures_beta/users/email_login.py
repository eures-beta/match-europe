"""Availability of transactional login email, shared by account workflows."""

from urllib.parse import urlsplit
from django.conf import settings
from eures_beta.emails.backend import real_email_allowed
from eures_beta.emails.rendering import html_email


def email_ready():
    origin = urlsplit(settings.LOGIN_EMAIL_ORIGIN)
    return bool(
        real_email_allowed()
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


def send_sign_in_link(user_id, language='fr'):
    """Invite a precreated employer through the existing passwordless sign-in."""
    import logging
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.urls import reverse
    from django.utils import translation
    from django.utils.translation import gettext as _
    from sesame.utils import get_query_string
    from .models import User

    if not email_ready():
        return
    user = User.objects.filter(pk=user_id, kind='employer', is_active=True).first()
    if not user:
        return
    link = (
        settings.LOGIN_EMAIL_ORIGIN.rstrip('/')
        + reverse('magic_confirm')
        + get_query_string(user)
    )
    with translation.override(language if language in ('fr', 'en', 'de') else 'fr'):
        body = render_to_string('users/login_email.txt', {'link': link})
        try:
            send_mail(
                _('Your Match Europe sign-in link'),
                body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_email(body),
            )
        except Exception:
            logging.getLogger(__name__).error(
                'Employer sign-in email delivery failed; inspect the mail service privately.'
            )
