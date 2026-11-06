from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.utils import translation
from django.utils.translation import gettext_lazy as _


@never_cache
@require_safe
def home(request):
    return _public_page(request, 'home.html')


@never_cache
@require_safe
def privacy(request):
    return _public_page(request, 'data_protection.html')


@never_cache
@require_safe
def statistics(request):
    return _public_page(request, 'under_construction.html', {'title': _('Statistics')})


@never_cache
@require_safe
def project(request):
    return _public_page(request, 'project.html', {'title': _('The project')})


@never_cache
@require_safe
def journal(request):
    from eures_beta.journal import ENTRIES

    return _public_page(request, 'journal.html', {'entries': ENTRIES})


def _public_page(request, template, context=None):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    with translation.override(language):
        return render(request, template, context)


def manifest(request):
    return JsonResponse(
        {
            'name': 'Match Europe',
            'short_name': 'Match Europe',
            'start_url': '/',
            'scope': '/',
            'display': 'standalone',
            'theme_color': '#003399',
            'background_color': '#f5f7fb',
            'icons': [
                {
                    'src': '/static/icon.svg',
                    'sizes': 'any',
                    'type': 'image/svg+xml',
                    'purpose': 'any',
                }
            ],
        },
        content_type='application/manifest+json',
    )


def service_worker(request):
    response = HttpResponse(
        (settings.APPS_DIR / 'static' / 'sw.js').read_text(),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
