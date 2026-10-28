"""Candidate welcome screen only: no profile, upload or external request."""

from django.shortcuts import render
from django.utils import translation
from django.views.decorators.http import require_safe

from eures_beta.demo_access import require_demo_access


@require_demo_access
@require_safe
def landing(request):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    with translation.override(language):
        return render(request, 'candidates/landing.html')
