"""Shared public team contact, independent of the visitor's role."""

from django.conf import settings


def context(request):
    return {'team_contact_email': settings.TEAM_CONTACT_EMAIL}
