from ipaddress import ip_address
from django.conf import settings
from django.http import Http404
from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer


def enabled():
    return (
        settings.MATCHING_LOCAL_ENABLED
        and settings.DJANGO_ENVIRONMENT == 'local'
        and not settings.EMAIL_DELIVERY_ENABLED
        and not settings.LOGIN_EMAIL_ENABLED
        and not settings.SHARED_DEMO
    )


def guard(request):
    try:
        local = ip_address(request.META.get('REMOTE_ADDR', '')).is_loopback
    except ValueError:
        local = False
    # Never trust forwarding headers as proof of a local connection.
    if not enabled() or not local:
        raise Http404


def candidates():
    return CandidateProfile.objects.filter(
        user__email__iendswith='.invalid',
        user__is_active=True,
        user__kind='candidate',
        email_verified_at__isnull=False,
    ).select_related('user')


def offers():
    return JobOffer.objects.filter(
        email__iendswith='.invalid',
        created_by__email__iendswith='.invalid',
        created_by__is_active=True,
        created_by__kind='employer',
        validated_at__isnull=False,
    )
