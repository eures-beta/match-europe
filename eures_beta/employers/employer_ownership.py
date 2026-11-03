"""Shared employer workspace permissions. Never infer membership from contact data."""

from django.db.models import Q
from eures_beta.employers.models import (
    JobOffer,
    CompanyMembership,
)


def identity(request):
    user = request.user
    if user.is_authenticated and user.is_active and user.kind == 'employer':
        return user
    return None


def memberships(request):
    person = identity(request)
    return (
        CompanyMembership.objects.filter(person=person, active=True)
        if person
        else CompanyMembership.objects.none()
    )


def accessible_imports(request):
    companies = memberships(request).values('company_id')
    allowed = Q(company_id__in=companies)
    person = identity(request)
    if person:
        allowed |= Q(company__isnull=True, created_by=person)
    # Legacy/unclaimed drafts remain private to their original browser only.
    if request.session.session_key:
        allowed |= Q(
            company__isnull=True,
            created_by__isnull=True,
            session_key=request.session.session_key,
        )
    return JobOffer.objects.filter(allowed)
