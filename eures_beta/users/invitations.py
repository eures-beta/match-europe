"""Explicit adviser invitations, separate from sign-in for existing accounts."""

from datetime import timedelta
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext as _

from .models import EmployerInvitation, LoginRateLimit, User, invitation_expiry
from .permissions import can_manage_employers

SALT = 'users.employer-invitation.v1'


def invitation_token(invitation):
    return signing.dumps(
        {'id': str(invitation.pk), 'nonce': str(invitation.nonce)}, salt=SALT
    )


def find_invitation(token, *, lock=False):
    try:
        data = signing.loads(
            token, salt=SALT, max_age=settings.EMPLOYER_INVITATION_MAX_AGE
        )
        identifier = uuid.UUID(data['id'])
        nonce = uuid.UUID(data['nonce'])
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        return None
    queryset = (
        EmployerInvitation.objects.select_for_update(of=('self',))
        if lock
        else EmployerInvitation.objects
    )
    return queryset.filter(
        pk=identifier,
        nonce=nonce,
        accepted_at__isnull=True,
        expires_at__gt=timezone.now(),
        invited_by__is_active=True,
        invited_by__kind=User.Kind.ADVISER,
    ).first()


@transaction.atomic
def create_invitation(adviser, email, language):
    # Serialize simultaneous invitations by one adviser, including the rate limit.
    adviser = User.objects.select_for_update().get(pk=adviser.pk)
    if not can_manage_employers(adviser):
        raise ValidationError(_('You are not allowed to invite employers.'))
    email = email.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError(_('An account already exists for this email address.'))
    now = timezone.now()
    key = salted_hmac('employer-invitation-limit', str(adviser.pk)).hexdigest()
    bucket, _created = LoginRateLimit.objects.get_or_create(
        key=key, defaults={'expires': now + timedelta(hours=1)}
    )
    if bucket.expires <= now:
        bucket.attempts = 0
        bucket.expires = now + timedelta(hours=1)
    if bucket.attempts >= 10:
        raise ValidationError(_('Too many invitations. Please try again later.'))
    invitation = (
        EmployerInvitation.objects.select_for_update()
        .filter(email__iexact=email)
        .first()
    )
    if invitation and (invitation.accepted_at or not invitation.expired):
        raise ValidationError(_('An invitation already exists for this email address.'))
    if invitation:
        invitation.nonce = uuid.uuid4()
        invitation.created_at = now
        invitation.expires_at = invitation_expiry()
        invitation.invited_by = adviser
        invitation.language = language
        invitation.email_sent_at = None
        invitation.save()
    else:
        invitation = EmployerInvitation.objects.create(
            email=email, language=language, invited_by=adviser
        )
    bucket.attempts += 1
    bucket.save(update_fields=['attempts', 'expires'])
    return invitation


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


def invitation_message(invitation, origin):
    origin = validate_origin(origin)
    if invitation.accepted_at or invitation.expired:
        raise ValidationError('Invitation already used or expired.')
    link = (
        origin.rstrip('/')
        + reverse('employer_invitation_confirm')
        + '?invitation='
        + invitation_token(invitation)
    )
    with translation.override(invitation.language):
        return (
            _('Your invitation to Match Europe'),
            render_to_string(
                'users/invitation_email.txt',
                {'link': link, 'expires_at': invitation.expires_at},
            ),
        )
