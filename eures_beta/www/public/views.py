from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from eures_beta.demo_access import require_demo_access


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


@require_demo_access
@require_safe
def design_system(request):
    """Team reference page: tokens and Bootstrap components with the ECL values."""
    from eures_beta import design_system as tokens

    return render(
        request,
        'design_system.html',
        {
            'role_colours': tokens.colour_tokens('--me-color-'),
            'palette_colours': tokens.colour_tokens('--me-palette-'),
            'font_sizes': tokens.scale_tokens('--me-font-size-'),
            'spaces': tokens.scale_tokens('--me-space-'),
            'radii': tokens.scale_tokens('--me-radius-'),
        },
    )


@require_demo_access
@require_safe
def design_system_example(request, screen='offre'):
    """Fictional screens built only with the design system."""
    screens = {
        'offre': 'Employeur · vérifier une offre',
        'mes-offres': 'Employeur · mes offres',
        'connexion': 'Connexion',
        'candidat': 'Candidat · questionnaire',
        'conseiller': 'Conseiller · offres à valider',
    }
    if screen not in screens:
        raise Http404()
    fonts = {
        'arial': 'Arial',
        'georgia': 'Georgia',
        'gelasio': 'Gelasio',
        'playfair': 'Playfair Display',
    }
    heading_font = request.GET.get('titres', 'arial')
    if heading_font not in fonts:
        heading_font = 'arial'
    return render(
        request,
        f'design_system/{screen}.html',
        {
            'screens': screens.items(),
            'screen': screen,
            'screen_label': screens[screen],
            'heading_fonts': fonts.items(),
            'heading_font': heading_font,
        },
    )


def _public_page(request, template, context=None):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    with translation.override(language):
        return render(request, template, context)


@require_safe
def manifest(request):
    from eures_beta.users.test_accounts import enabled, fictional_database

    preview = (
        settings.DJANGO_ENVIRONMENT == 'preview' and enabled() and fictional_database()
    )
    return JsonResponse(
        {
            'name': 'Match Europe',
            'short_name': 'Match Europe',
            'id': '/',
            'start_url': reverse('test_accounts' if preview else 'home'),
            'scope': '/',
            'display': 'standalone',
            'theme_color': '#125640' if preview else '#003399',
            'background_color': '#f5f7fb',
            'icons': [
                {
                    'src': static(f'pwa/icon-{size}.png'),
                    'sizes': f'{size}x{size}',
                    'type': 'image/png',
                    'purpose': 'any',
                }
                for size in (192, 512)
            ],
        },
        content_type='application/manifest+json',
    )


@require_safe
def service_worker(request):
    response = HttpResponse(
        (settings.APPS_DIR / 'static' / 'sw.js').read_text(),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
