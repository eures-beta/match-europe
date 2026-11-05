"""Explicit candidate signup trial; login for existing accounts remains separate."""

import json
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from eures_beta.users.invitations import validate_origin
from eures_beta.users.models import User
from .models import CandidateProfile, CandidateRegistration

SALT = 'candidates.registration.v1'


def enabled():
    return (
        settings.CANDIDATE_REGISTRATION_ENABLED
        and settings.DJANGO_ENVIRONMENT in ('local', 'preview')
        and not settings.EMAIL_DELIVERY_ENABLED
    )


def require_trial():
    if not enabled():
        raise Http404()


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
    query = (
        CandidateRegistration.objects.select_for_update()
        if lock
        else CandidateRegistration.objects
    )
    return query.filter(
        pk=identifier, nonce=nonce, expires_at__gt=timezone.now()
    ).first()


@transaction.atomic
def create_request(email, data, language):
    require_trial()
    email = email.strip().lower()
    validate_email(email)
    if not email.endswith('.invalid'):
        raise ValidationError('Fictional addresses only.')
    answers = validated_answers(data, language)
    CandidateRegistration.objects.filter(expires_at__lte=timezone.now()).delete()
    existing = User.objects.filter(email__iexact=email).first()
    if existing and (
        not existing.is_active
        or existing.kind != User.Kind.CANDIDATE
        or CandidateProfile.objects.filter(user=existing).exists()
    ):
        return None
    # Do not replace an unverified request: an anonymous visitor cannot change
    # the answers another person is currently verifying.
    if CandidateRegistration.objects.filter(email__iexact=email).exists():
        return None
    return CandidateRegistration.objects.create(
        email=email, language=language, answers=answers
    )


@transaction.atomic
def confirm_registration(token):
    require_trial()
    pending = find_registration(token, lock=True)
    if pending is None:
        return None
    user = User.objects.select_for_update().filter(email__iexact=pending.email).first()
    if user and (
        not user.is_active
        or user.kind != User.Kind.CANDIDATE
        or CandidateProfile.objects.filter(user=user).exists()
    ):
        pending.delete()
        return None
    if user is None:
        user = User.objects.create_user(email=pending.email, kind=User.Kind.CANDIDATE)
    answers = validated_answers(pending.answers, pending.language)
    for name in ('salary_amount', 'available_from'):
        if answers.get(name) == '':
            answers[name] = None
    CandidateProfile.objects.create(
        user=user,
        language=pending.language,
        email_verified_at=timezone.now(),
        notice_read_at=pending.created_at,
        notice_version='2026-11-05',
        **answers,
    )
    pending.delete()
    return user


def simulated_email(pending, origin):
    require_trial()
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


def profile_answers(profile):
    excluded = {'id', 'user', 'created_at', 'updated_at', 'language'}
    data = model_to_dict(profile, exclude=excluded)
    return json.loads(json.dumps(data, default=str))


@transaction.atomic
def update_profile(user, data, language):
    require_trial()
    if (
        not user.is_authenticated
        or not user.is_active
        or user.kind != User.Kind.CANDIDATE
    ):
        raise PermissionDenied
    profile = CandidateProfile.objects.select_for_update().get(user=user)
    answers = validated_answers(data, language)
    for name, value in answers.items():
        if name in ('salary_amount', 'available_from') and value == '':
            value = None
        setattr(profile, name, value)
    profile.language = language
    profile.save()
    return profile
