"""Deposit and telephone confirmation without manufacturing employer accounts."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from eures_beta.users.models import User


def guard(user):
    if not user.is_authenticated or not user.is_active or user.kind != 'adviser':
        raise PermissionDenied


def confirm(offer, adviser, date):
    guard(adviser)
    if not date or date > timezone.localdate():
        raise ValidationError(
            _('Enter the date of the telephone confirmation, no later than today.')
        )
    if not all(
        offer.data.get(key)
        for key in ('title', 'companyName', 'city', 'description', 'contractType')
    ):
        raise ValidationError(
            _(
                'Complete job title, company, location, description and contract type before confirming.'
            )
        )
    offer.phone_confirmed_on = date
    offer.phone_recorded_at = timezone.now()
    offer.phone_confirmed_revision = offer.revision
    offer.validated_at = timezone.now()


def check_employer(email):
    user = User.objects.filter(email__iexact=email).first()
    if user and user.kind != User.Kind.EMPLOYER:
        raise ValidationError(
            _('This email belongs to an account that is not an employer.')
        )
    if user and not user.is_active:
        raise ValidationError(_('This employer account is disabled.'))
    return user


@transaction.atomic
def create(offer, adviser, setup, *, language='fr'):
    guard(adviser)
    User.objects.select_for_update().get(pk=adviser.pk)
    existing = type(offer).objects.filter(pk=setup['offer_id'], adviser=adviser).first()
    if existing:
        return existing
    from django.core.validators import validate_email

    email = setup['email'].strip().lower()
    validate_email(email)
    employer, _ = User.objects.get_or_create(
        email__iexact=email,
        defaults={
            'email': email,
            'kind': User.Kind.EMPLOYER,
            'is_active': True,
            'password': '!',
        },
    )
    employer = User.objects.select_for_update().get(pk=employer.pk)
    check_employer(email)
    offer.pk = setup['offer_id']
    offer.created_by = employer
    offer.adviser = adviser
    offer.contact = {
        key: value for key, value in offer.contact.items() if key != 'email'
    }
    offer.save()
    from eures_beta.users.email_login import send_sign_in_link

    transaction.on_commit(lambda: send_sign_in_link(employer.pk, language))
    return offer
