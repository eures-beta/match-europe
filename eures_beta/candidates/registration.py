"""Verified candidate signup; login for existing accounts remains separate."""

import json
import logging
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms.models import model_to_dict
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from eures_beta.users.invitations import validate_origin
from eures_beta.users.models import User
from .models import CandidateProfile
from . import pending as pending_store
from dataclasses import dataclass

SALT = 'candidates.registration.v1'
logger = logging.getLogger(__name__)


def validated_answers(data, language):
    from .journey import ProjectForm, MobilityForm, ConditionsForm

    names = {field.name for field in CandidateProfile._meta.fields} - {
        'id',
        'user',
        'created_at',
        'updated_at',
        'language',
    }
    answers = {'display_name': str(data.get('display_name', '')).strip()}
    if not 0 < len(answers['display_name']) <= 150:
        raise ValidationError('Invalid display name.')
    for form_class in (ProjectForm, MobilityForm, ConditionsForm):
        form = form_class(
            data, **({'language': language} if form_class is ProjectForm else {})
        )
        if not form.is_valid():
            raise ValidationError('Invalid candidate answers.')
        answers.update(
            {name: value for name, value in form.cleaned_data.items() if name in names}
        )
    # Only the validated model fields are stored, never the entire draft or UI flags.
    return json.loads(json.dumps(answers, default=str))


def token_for(registration):
    return signing.dumps(
        {'id': str(registration.pk), 'nonce': str(registration.nonce)}, salt=SALT
    )


def find_registration(token, *, lock=False):
    try:
        payload = signing.loads(
            token, salt=SALT, max_age=settings.CANDIDATE_REGISTRATION_MAX_AGE
        )
        identifier, nonce = uuid.UUID(payload['id']), uuid.UUID(payload['nonce'])
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        return None
    return pending_store.load(identifier, nonce, lock=lock)


@transaction.atomic
def create_request(email, data, language):
    email = email.strip().lower()
    validate_email(email)
    answers = validated_answers(data, language)
    pending_store.expired().delete()
    # Independent packages: a second visitor cannot overwrite another draft.
    # Account existence is only disclosed after proving possession of the email.
    return pending_store.store(email, answers, language)


@dataclass
class Confirmation:
    user: object
    pending: object
    status: str


@transaction.atomic
def confirm_registration(token):
    pending = find_registration(token, lock=True)
    if pending is None:
        return None
    user = User.objects.select_for_update().filter(email__iexact=pending.email).first()
    if user and (not user.is_active or user.kind != User.Kind.CANDIDATE):
        pending.delete()
        return Confirmation(None, pending, 'role')
    if user is None:
        user = User.objects.create_user(email=pending.email, kind=User.Kind.CANDIDATE)
    answers = validated_answers(pending.answers, pending.language)
    for name in ('salary_amount', 'available_from'):
        if answers.get(name) == '':
            answers[name] = None
    existing = CandidateProfile.objects.filter(user=user).exists()
    if not existing:
        CandidateProfile.objects.create(
            user=user,
            language=pending.language,
            email_verified_at=timezone.now(),
            notice_read_at=pending.created_at,
            notice_version='2026-11-05',
            **answers,
        )
    pending.delete()
    return Confirmation(user, pending, 'review' if existing else 'created')


def confirmation_message(pending, origin):
    if pending.expires_at <= timezone.now():
        raise ValidationError('Expired request.')
    link = (
        validate_origin(origin)
        + reverse('candidate_registration_confirm')
        + '?'
        + urlencode({'token': token_for(pending)})
    )
    with translation.override(pending.language):
        return (
            _('Confirm your candidate profile'),
            render_to_string('candidates/registration_email.txt', {'link': link}),
        )


def send_confirmation(pending):
    # Same protected Django delivery policy as sign-in and employer invitations.
    # No candidate-specific environment switch and no transport bypass.
    from eures_beta.users.views import email_ready

    if pending is None or not email_ready():
        return False
    try:
        subject, body = confirmation_message(pending, settings.LOGIN_EMAIL_ORIGIN)
        return bool(
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [pending.email])
        )
    except Exception:
        logger.error(
            'Candidate confirmation email delivery failed; inspect the mail service privately.'
        )
        return False


def profile_answers(profile):
    excluded = {'id', 'user', 'created_at', 'updated_at', 'language'}
    data = model_to_dict(profile, exclude=excluded)
    return json.loads(json.dumps(data, default=str))


class StaleProfile(ValidationError):
    pass


@transaction.atomic
def update_profile(user, data, language, *, expected_updated_at=None):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.kind != User.Kind.CANDIDATE
    ):
        raise PermissionDenied
    profile = CandidateProfile.objects.select_for_update().get(user=user)
    if expected_updated_at and profile.updated_at.isoformat() != expected_updated_at:
        raise StaleProfile('The profile changed. Review it again before updating.')
    answers = validated_answers(data, language)
    for name, value in answers.items():
        if name in ('salary_amount', 'available_from') and value == '':
            value = None
        setattr(profile, name, value)
    profile.language = language
    profile.save()
    return profile
