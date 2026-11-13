"""The public landing stays open; importing requires an existing employer account."""

from functools import wraps
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import translation

from eures_beta.employers.employer_ownership import identity
from eures_beta.www.accounts.return_path import IMPORT_PATHS


def access_page(request, path):
    language = path.rsplit('-', 1)[-1].removesuffix('.html')
    language = request.GET.get('lang', language)
    language = language if language in ('fr', 'en', 'de') else 'fr'
    destination = '/employer/pages/' + path
    if destination not in IMPORT_PATHS:
        destination = f'/employer/pages/import-{language}.html'
    else:
        destination = destination.rsplit('-', 1)[0] + '-' + language + '.html'
    request.session['login_return_path'] = destination
    with translation.override(language):
        return render(
            request,
            'employer/import_access.html',
            {
                'import_login_query': urlencode(
                    {'next': destination, 'lang': language}
                ),
            },
        )


def employer_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not identity(request):
            return JsonResponse({'error': 'employer_account_required'}, status=403)
        return view(request, *args, **kwargs)

    return wrapped
