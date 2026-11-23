"""Consolidate the two historical demo employers without deleting their history."""

from django.core.management import CommandError
from django.db import transaction

from eures_beta.employers.models import EmployerProfile, JobOffer
from eures_beta.matching.models import CandidateOfferConversation

from .models import User
from .test_accounts import ACCOUNTS, enabled, fictional_database

LEGACY_EMPLOYER_EMAIL = 'employer@matching-trial.invalid'


@transaction.atomic
def consolidate_employers():
    """Keep content and author identities; retire only the old demo sign-in."""
    if not enabled() or not fictional_database():
        raise CommandError(
            'Demo consolidation requires an isolated fictional database.'
        )
    emails = (ACCOUNTS['employer']['email'], LEGACY_EMPLOYER_EMAIL)
    users = {
        user.email.lower(): user
        for user in User.objects.select_for_update()
        .filter(email__in=emails)
        .order_by('pk')
    }
    legacy = users.get(LEGACY_EMPLOYER_EMAIL)
    if legacy is None:
        return
    employer = users.get(ACCOUNTS['employer']['email'])
    if employer is None or not employer.is_active:
        raise CommandError('The destination demo employer must be prepared first.')
    for user in (employer, legacy):
        if (
            user.kind != User.Kind.EMPLOYER
            or user.is_staff
            or user.is_superuser
            or user.has_usable_password()
        ):
            raise CommandError(
                'A demo employer has unexpected attributes; no data changed.'
            )

    # Content, timestamps, revisions, answer/consent fingerprints and IDs stay intact.
    JobOffer.objects.filter(employer=legacy).update(employer=employer)
    CandidateOfferConversation.objects.filter(employer=legacy).update(employer=employer)
    if not EmployerProfile.objects.filter(user=employer).exists():
        EmployerProfile.objects.filter(user=legacy).update(user=employer)

    updates = {
        field: getattr(legacy, field)
        for field in ('first_name', 'last_name', 'organization_name')
        if not getattr(employer, field) and getattr(legacy, field)
    }
    if updates:
        User.objects.filter(pk=employer.pk).update(**updates)

    # Existing message authors, accepted invitations, admin logs and a possibly
    # different second personal profile remain auditable on this inactive account.
    # No identity is rewritten and no conflicting profile value is discarded.
    if legacy.is_active:
        legacy.is_active = False
        legacy.save(update_fields=['is_active'])
