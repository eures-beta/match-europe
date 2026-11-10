"""Candidate welcome screen only: no profile, upload or external request."""

from django.shortcuts import render
from django.utils import translation
from django.views.decorators.http import require_safe

from django.views.decorators.cache import never_cache


@never_cache
@require_safe
def landing(request):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    with translation.override(language):
        return render(request, 'candidates/landing.html')


@require_safe
def install(request):
    from eures_beta.users.views import selected_language

    with translation.override(selected_language(request)):
        return render(request, 'candidates/install.html')
