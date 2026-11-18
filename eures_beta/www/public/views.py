from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
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


@never_cache
@require_safe
def design_system(request):
    """Public reference reached by its URL, outside the product navigation."""
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


@never_cache
@require_safe
def design_system_example(request, screen='offre'):
    """Fictional screens built only with the design system."""
    screens = {
        'offre': 'Employeur · vérifier une offre',
        'mes-offres': 'Employeur · mes offres',
        'connexion': 'Connexion',
        'candidat': 'Candidat · questionnaire',
        'conseiller': 'Conseiller · offres à valider',
        # Real employer pages redressed: same content and structure, fictional data.
        'employeur-accueil': 'Employeur · accueil',
        'employeur-tableau-de-bord': 'Employeur · tableau de bord',
        'employeur-offres': 'Employeur · espace et offres',
        'employeur-ajout': 'Employeur · ajouter une offre',
        'employeur-offre': 'Employeur · détail d’une offre',
        'employeur-modifier': 'Employeur · modifier une offre',
    }
    if screen not in screens:
        raise Http404()
    return render(
        request,
        f'design_system/{screen}.html',
        {
            'screens': screens.items(),
            'screen': screen,
            'screen_label': screens[screen],
            'connected': screen != 'employeur-accueil',
            'conditions': [
                'Tôt le matin',
                'Travail de nuit',
                'Week-end',
                'Horaires variables',
                'Travail posté',
                'Travail physique',
                'Station debout prolongée',
                'Horaires avec coupure',
                'Travail en extérieur',
                'Déplacements fréquents',
                'Aucune',
                'À discuter',
            ],
            'licences': ['B', 'C', 'CE', 'D', 'DE', 'CACES', 'Autre'],
            'arrival_help': [
                'Logement',
                'Démarches administratives',
                'Transport',
                'Accompagnement à la prise de poste',
                'Autre',
                'Aucune',
                'À discuter',
            ],
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
