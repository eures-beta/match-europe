"""Contact for employers requesting a Match Europe invitation."""

from django.conf import settings


def adviser_contact_url(language=None):
    """Return the team contact unchanged, including mailto URLs."""
    return settings.EMPLOYER_ADVISER_CONTACT_URL


def context(request):
    return {"employer_adviser_contact_url": adviser_contact_url()}
