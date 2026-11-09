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
from datetime import timedelta

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


def token_for(user):
    return signing.dumps(
        {'id': user.pk, 'nonce': str(user.candidate_verification_nonce)}, salt=SALT
    )


def find_registration(token, *, lock=False):
    try:
        payload = signing.loads(
            token, salt=SALT, max_age=settings.CANDIDATE_REGISTRATION_MAX_AGE
        )
        identifier, nonce = int(payload['id']), uuid.UUID(payload['nonce'])
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        return None
    query = User.objects.select_for_update() if lock else User.objects
    return query.filter(
        pk=identifier,
        kind=User.Kind.CANDIDATE,
        is_active=False,
        candidate_verification_nonce=nonce,
        candidate_verification_expires__gt=timezone.now(),
    ).first()


@transaction.atomic
def create_request(email, language):
    email = email.strip().lower()
    validate_email(email)
    existing = User.objects.select_for_update().filter(email__iexact=email).first()
    if existing:
        # Never modify an existing account/profile from an anonymous request.
        # Active accounts receive the ordinary sign-in link, including other roles.
        if existing.is_active:
            return existing
        if (
            existing.kind == User.Kind.CANDIDATE
            and existing.candidate_verification_nonce
        ):
            if existing.candidate_verification_expires <= timezone.now():
                existing.candidate_verification_nonce = uuid.uuid4()
                existing.candidate_verification_expires = timezone.now() + timedelta(
                    seconds=settings.CANDIDATE_REGISTRATION_MAX_AGE
                )
                existing.save(
                    update_fields=[
                        'candidate_verification_nonce',
                        'candidate_verification_expires',
                    ]
                )
            return existing
        return None
    return User.objects.create_user(
        email=email,
        kind=User.Kind.CANDIDATE,
        is_active=False,
        candidate_verification_nonce=uuid.uuid4(),
        candidate_verification_expires=timezone.now()
        + timedelta(seconds=settings.CANDIDATE_REGISTRATION_MAX_AGE),
        candidate_verification_language=language,
    )


@transaction.atomic
def confirm_registration(token):
    user = find_registration(token, lock=True)
    if user is None:
        return None
    user.is_active = True
    user.candidate_verification_nonce = None
    user.candidate_verification_expires = None
    user.save(
        update_fields=[
            'is_active',
            'candidate_verification_nonce',
            'candidate_verification_expires',
        ]
    )
    return user


def confirmation_message(user, origin):
    origin = validate_origin(origin)
    if user.is_active:
        from sesame.utils import get_query_string

        link = origin + reverse('magic_confirm') + get_query_string(user)
    else:
        if (
            not user.candidate_verification_nonce
            or user.candidate_verification_expires <= timezone.now()
        ):
            raise ValidationError('Expired request.')
        link = (
            origin
            + reverse('candidate_registration_confirm')
            + '?'
            + urlencode({'token': token_for(user)})
        )
    with translation.override(user.candidate_verification_language):
        return (
            _('Confirm your email to continue'),
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


@transaction.atomic
def update_profile(user, data, language):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.kind != User.Kind.CANDIDATE
    ):
        raise PermissionDenied
    User.objects.select_for_update().get(pk=user.pk)
    profile = CandidateProfile.objects.select_for_update().filter(user=user).first()
    if profile is None:
        answers = validated_answers(data, language)
        for name in ("salary_amount", "available_from"):
            if answers.get(name) == "":
                answers[name] = None
        return CandidateProfile.objects.create(
            user=user,
            language=language,
            email_verified_at=timezone.now(),
            notice_read_at=timezone.now(),
            notice_version="2026-11-05",
            **answers,
        )
    answers = validated_answers(data, language)
    for name, value in answers.items():
        if name in ('salary_amount', 'available_from') and value == '':
            value = None
        setattr(profile, name, value)
    profile.language = language
    profile.save()
    return profile
