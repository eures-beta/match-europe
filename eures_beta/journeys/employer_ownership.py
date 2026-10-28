"""Shared employer workspace permissions. Never infer membership from contact data."""

from django.db.models import Q
from eures_beta.journeys.models import (
    EmployerIdentity,
    EmployerImport,
    EmployerMembership,
)


def identity(request):
    person_id = request.session.get('employer_identity_id')
    if not person_id:
        return None
    return EmployerIdentity.objects.filter(pk=person_id).first()


def memberships(request):
    person = identity(request)
    return (
        EmployerMembership.objects.filter(person=person, active=True)
        if person
        else EmployerMembership.objects.none()
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
    return EmployerImport.objects.filter(allowed)
