"""Explicit import and candidate-dialogue destinations, never arbitrary next URLs."""

from urllib.parse import parse_qs, urlencode, urlsplit

from django.http import Http404
from django.urls import Resolver404, resolve, reverse


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
            try:
                match = resolve(url.path)
            except Resolver404:
                match = None
            if match and match.url_name == 'candidate_offer_dialogue':
                path = reverse('candidate_offer_dialogue', kwargs=match.kwargs)
                return path + ('?' + urlencode({'lang': language}) if language else '')
            from eures_beta.www.public.redirects import old_import_destination

            old_path, old_language = old_import_destination(url.path)
            if not old_path:
                return ''
            language = language or old_language
        return path + ('?' + urlencode({'lang': language}) if language else '')
    except (ValueError, Http404):
        return ''


def is_import_destination(destination):
    return (
        bool(destination)
        and canonical_destination(destination) == destination
        and urlsplit(destination).path == reverse('employer_import')
    )


def remember(request):
    destination = canonical_destination(request.GET.get('next', ''))
    if destination:
        request.session['login_return_path'] = destination
        language = parse_qs(urlsplit(destination).query).get('lang', [''])[0]
        if language:
            request.session['login_language'] = language


def consume(request, default, *, user=None):
    destination = canonical_destination(request.session.pop('login_return_path', ''))
    user = request.user if user is None else user
    if destination:
        kind = 'employer' if is_import_destination(destination) else 'candidate'
        if user.is_authenticated and user.is_active and user.kind == kind:
            return destination
    return default
