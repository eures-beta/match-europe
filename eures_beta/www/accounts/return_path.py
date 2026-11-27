"""Explicit journey destinations, never arbitrary next URLs."""

from urllib.parse import parse_qs, urlencode, urlsplit

from django.http import Http404
from django.urls import Resolver404, resolve, reverse


def canonical_destination(destination):
    try:
        url = urlsplit(destination)
        if url.scheme or url.netloc or url.fragment:
            return ''
        query = parse_qs(url.query, keep_blank_values=True)
        planning = url.path == reverse('staff_planning')
        if planning and 'week' in query:
            from datetime import date

            values = query['week']
            if (
                len(values) != 1
                or date.fromisoformat(values[0]).isoformat() != values[0]
            ):
                return ''
        if (
            set(query) - ({'lang', 'week'} if planning else {'lang'})
            or len(query.get('lang', [])) > 1
        ):
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
            if match and match.url_name in {
                'staff_planning',
                'candidate_offer_dialogue',
                'candidate_offer_confirmation',
                'adviser_followup_list',
                'adviser_match_lifecycle',
                'report_match_hiring',
                'shared_conversation',
                'respond_employer_consent',
            }:
                path = reverse(match.url_name, kwargs=match.kwargs)
                parameters = {'lang': language} if language else {}
                if planning and query.get('week'):
                    parameters['week'] = query['week'][0]
                return path + ('?' + urlencode(parameters) if parameters else '')
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
    if destination and urlsplit(destination).path == reverse('staff_planning'):
        return (
            destination
            if user.is_authenticated and user.is_active and user.is_staff
            else default
        )
    if destination:
        kind = 'employer' if is_import_destination(destination) else 'candidate'
        if user.is_authenticated and user.is_active and user.kind == kind:
            return destination
    return default
