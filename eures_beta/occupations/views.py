"""Local reference search for the prototype, behind the shared demo access gate."""

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from eures_beta.demo_access import require_demo_access
from .catalog import catalog, occupation_index, nearby, suggestions


@require_demo_access
@require_http_methods(['GET', 'POST'])
def search_api(request):
    if request.method == 'POST':
        if len(request.body) > 80000:
            return JsonResponse({'error': 'invalid_data'}, status=400)
        try:
            data = json.loads(request.body)
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'error': 'invalid_data'}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({'error': 'invalid_data'}, status=400)
        excluded = data.get('excluded', [])
    else:
        data = request.GET
        excluded = data.getlist('excluded')
    language = data.get('lang', 'fr')
    query = data.get('q', '')
    mode = data.get('mode', 'search')
    context = data.get('context', '')
    if (
        language not in ('fr', 'en', 'de')
        or not isinstance(query, str)
        or not 1 <= len(query) <= 150
        or mode not in ('search', 'near')
        or not isinstance(context, str)
        or len(context) > 20000
        or not isinstance(excluded, list)
        or len(excluded) > 100
        or any(
            not isinstance(uri, str) or uri not in occupation_index()
            for uri in excluded
        )
    ):
        return JsonResponse({'error': 'invalid_data'}, status=400)
    rows = (
        nearby(query, language, excluded, context)
        if mode == 'near'
        else suggestions(query, language, context)
    )
    return JsonResponse({'version': catalog()['manifest']['version'], 'results': rows})
