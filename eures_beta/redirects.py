"""Compatibility redirects for documents already open before the URL migration."""

from django.http import Http404, HttpResponsePermanentRedirect
from django.urls import reverse
from django.views.decorators.http import require_safe

LEGACY_EMPLOYER_PAGES = {
    f'{prefix}{language}.html'
    for prefix in ('', 'import-', 'import-v2-', 'privacy-')
    for language in ('fr', 'en', 'de')
}


@require_safe
def legacy_home(request):
    url = reverse('home')
    query = request.META.get('QUERY_STRING')
    if query:
        url += '?' + query
    return HttpResponsePermanentRedirect(url)


@require_safe
def legacy_employer_page(request, path):
    if path not in LEGACY_EMPLOYER_PAGES:
        raise Http404
    url = '/employer/pages/' + path
    query = request.META.get('QUERY_STRING')
    if query:
        url += '?' + query
    return HttpResponsePermanentRedirect(url)
