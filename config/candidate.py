"""Language-preserving entry to the candidate's first screen."""

from pathlib import Path

from django.http import FileResponse, Http404, HttpResponseRedirect
from django.views.decorators.http import require_safe
from journeys.employer_api import demo_api

PREVIEW = Path(__file__).resolve().parents[1] / 'previews' / 'employer-landing'


@require_safe
def candidate_entry(request):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    return HttpResponseRedirect(f'/previews/employer-landing/candidate-{language}.html')


@demo_api
@require_safe
def candidate_page(request, language):
    if language not in ('fr', 'en', 'de'):
        raise Http404()
    return FileResponse(
        (PREVIEW / f'candidate-{language}.html').open('rb'),
        content_type='text/html; charset=utf-8',
    )


@demo_api
@require_safe
def candidate_asset(request, asset):
    if asset not in ('css', 'js'):
        raise Http404()
    content_type = 'text/css' if asset == 'css' else 'text/javascript'
    return FileResponse(
        (PREVIEW / f'candidate.{asset}').open('rb'), content_type=content_type
    )
