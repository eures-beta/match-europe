"""Where an employer without an invitation can find an EURES adviser."""

from urllib.parse import urlencode

from django.conf import settings
from django.utils import translation


def adviser_contact_url(language=None):
    """Return the configured adviser contact page, localised when it has no query."""
    url = settings.EMPLOYER_ADVISER_CONTACT_URL
    if not url or '?' in url:
        return url
    language = language or translation.get_language() or 'fr'
    return f"{url}?{urlencode({'lang': language[:2]})}"


def context(request):
    return {'employer_adviser_contact_url': adviser_contact_url()}
