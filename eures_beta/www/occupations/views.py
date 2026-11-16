"""Public read-only reference search used by candidate and employer forms."""

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from eures_beta.occupations.catalog import (
    catalog,
    occupation_index,
    nearby,
    suggestions,
    references,
    rome_suggestions,
    looks_like_reference,
    is_rome_reference,
)


@never_cache
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
    independent = data.get('independent', False)
    context = data.get('context', '')
    if (
        not isinstance(independent, bool)
        or language not in ('fr', 'en', 'de')
        or not isinstance(query, str)
        or not 1 <= len(query) <= 150
        or mode not in ('search', 'near', 'reference')
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
    if mode == 'search' and looks_like_reference(query):
        mode = 'reference'
    independent_rome_code = independent and is_rome_reference(query)
    rows = (
        []
        if independent_rome_code
        else (
            references(query, language)
            if mode == 'reference'
            else (
                nearby(query, language, excluded, context)
                if mode == 'near'
                else suggestions(query, language, context)
            )
        )
    )
    rome_rows = rome_suggestions(query, context) if independent else []
    if independent_rome_code:
        rows = []  # Never turn a ROME code into ESCO matches in the independent trial.
    return JsonResponse(
        {
            'rome_results': rome_rows,
            'rome_version': '26M10',
            'version': catalog()['manifest']['version'],
            'results': rows[:20],
            'total': len(rows),
        }
    )
