"""Retired addresses: bookmark/client compatibility only, scheduled for removal."""

from django.http import Http404, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe


@require_http_methods(['GET', 'HEAD', 'POST'])
def legacy_workspace_route(request, target, pk=None):
    destination = reverse(target, kwargs={'pk': pk} if pk is not None else None)
    query = request.META.get('QUERY_STRING', '')
    return HttpResponsePermanentRedirect(
        destination + ('?' + query if query else ''), preserve_request=True
    )


def employer_destination(path):
    for language in ('fr', 'en', 'de'):
        for prefix, name in (
            ('', 'employer_landing'),
            ('import-', 'employer_import'),
            ('import-v2-', 'employer_import'),
            ('privacy-', 'employer_privacy'),
        ):
            if path == prefix + language + '.html':
                return reverse(name), language
    raise Http404


def old_import_destination(path):
    # Only for a pending login/session created before this URL migration.
    for folder in ('/employer/pages/', '/previews/employer-landing/'):
        if path.startswith(folder):
            destination, language = employer_destination(path.removeprefix(folder))
            if destination == reverse('employer_import'):
                return destination, language
    return '', ''


def legacy_employer_page(request, path):
    destination, language = employer_destination(path)
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])
    query = request.GET.copy()
    if query.get('lang') not in ('fr', 'en', 'de'):
        query['lang'] = language
    return HttpResponsePermanentRedirect(destination + '?' + query.urlencode())


@require_safe
def legacy_employer_connected(request):
    query = request.META.get('QUERY_STRING', '')
    return HttpResponsePermanentRedirect(
        reverse('employer_offers') + ('?' + query if query else '')
    )


@require_http_methods(['GET', 'HEAD', 'POST'])
def legacy_import_api(request, id=None, source=False):
    name = (
        'job_offer_source' if source else 'job_offer_data' if id else 'job_offer_list'
    )
    destination = reverse(name, kwargs={'id': id} if id else None)
    query = request.META.get('QUERY_STRING', '')
    return HttpResponsePermanentRedirect(
        destination + ('?' + query if query else ''), preserve_request=True
    )
