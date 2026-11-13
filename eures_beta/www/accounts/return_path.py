"""A fixed import destination, not an arbitrary next URL."""

from urllib.parse import parse_qs, urlencode, urlsplit

from django.http import Http404
from django.urls import reverse


def canonical_destination(destination):
    try:
        url = urlsplit(destination)
        if url.scheme or url.netloc or url.fragment:
            return ''
        query = parse_qs(url.query, keep_blank_values=True)
        if set(query) - {'lang'} or len(query.get('lang', [])) > 1:
            return ''
        language = query.get('lang', [''])[0]
        if language and language not in ('fr', 'en', 'de'):
            return ''
        path = reverse('employer_import')
        if url.path != path:
            from eures_beta.www.public.redirects import old_import_destination

            old_path, old_language = old_import_destination(url.path)
            if not old_path:
                return ''
            language = language or old_language
        return path + ('?' + urlencode({'lang': language}) if language else '')
    except (ValueError, Http404):
        return ''


def is_import_destination(destination):
    return bool(destination) and canonical_destination(destination) == destination


def remember(request):
    destination = canonical_destination(request.GET.get('next', ''))
    if destination:
        request.session['login_return_path'] = destination
        language = parse_qs(urlsplit(destination).query).get('lang', [''])[0]
        if language:
            request.session['login_language'] = language


def consume(request, default):
    return (
        canonical_destination(request.session.pop('login_return_path', '')) or default
    )
