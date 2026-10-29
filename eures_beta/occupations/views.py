"""Local reference search for the prototype, behind the shared demo access gate."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from eures_beta.demo_access import require_demo_access
from .catalog import catalog, occupation_index, nearby, suggestions


@require_demo_access
@require_GET
def search_api(request):
    language = request.GET.get('lang', 'fr')
    query = request.GET.get('q', '').strip()
    excluded = request.GET.getlist('excluded')
    mode = request.GET.get('mode', 'search')
    if (
        language not in ('fr', 'en', 'de')
        or not 1 <= len(query) <= 150
        or mode not in ('search', 'near')
        or len(excluded) > 100
        or any(uri not in occupation_index() for uri in excluded)
    ):
        return JsonResponse({'error': 'invalid_data'}, status=400)
    rows = (
        nearby(query, language, excluded)
        if mode == 'near'
        else suggestions(query, language)
    )
    return JsonResponse({'version': catalog()['manifest']['version'], 'results': rows})
