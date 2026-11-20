from django.conf import settings
from django.db.models import Q, F
from django.core.exceptions import PermissionDenied
from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer


def test_data_enabled():
    from eures_beta.users.test_accounts import (
        enabled as demo_enabled,
        fictional_database,
    )

    return demo_enabled() and fictional_database()


def candidates():
    return CandidateProfile.objects.filter(
        user__is_active=True,
        user__kind='candidate',
        email_verified_at__isnull=False,
    ).select_related('user')


def employer_offers():
    return JobOffer.objects.filter(
        created_by__is_active=True, created_by__kind='employer'
    )


def offers():
    return employer_offers().filter(validated_at__isnull=False)


def matchable_offers():
    required = ('title', 'companyName', 'city', 'description', 'contractType')
    workspace_ready = Q(company__isnull=False, data__has_keys=required) & (
        Q(duplicated_from__isnull=True) | Q(revision__gt=1)
    )
    for field in required:
        workspace_ready &= ~Q(**{f'data__{field}': ''}) & ~Q(**{f'data__{field}': None})
    confirmation = Q(phone_recorded_at__isnull=True) | Q(
        adviser__isnull=False,
        phone_confirmed_on__isnull=False,
        phone_confirmed_revision=F('revision'),
    )
    return (
        employer_offers()
        .filter(confirmation)
        .filter(workspace_ready | Q(validated_at__isnull=False))
    )


def can_view_pairs(user):
    return user.is_authenticated and user.is_active and user.kind == 'adviser'


def can_change_match(user):
    return can_view_pairs(user)


def guard(request):
    if not can_view_pairs(request.user):
        raise PermissionDenied
