"""Explicit employer pages; templates are never selected from a URL path."""

from html import escape

from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import translation
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe

from eures_beta.employers.employer_ownership import identity
from eures_beta.www.accounts.views import selected_language
from .access import access_page


@never_cache
@ensure_csrf_cookie
@require_safe
def landing(request):
    return render_page(request, 'landing.html')


@never_cache
@ensure_csrf_cookie
@require_safe
def import_offer(request):
    if not identity(request):
        return access_page(request)
    return render_page(request, 'import.html')


@never_cache
@ensure_csrf_cookie
@require_safe
def privacy(request):
    return render_page(request, 'privacy.html')


def render_page(request, template, **extra_context):
    person = identity(request)
    adviser_setup = extra_context.get('adviser_setup')
    body_tag = (
        '<body data-employer-api="true" data-employer-connected="'
        + ('true' if person else 'false')
        + '"'
        + (
            ' data-employer-email="' + escape(person.email, quote=True) + '"'
            if person
            else ''
        )
        + (
            ' data-offer-api="/api/adviser/job-offers/" data-adviser-deposit="true" data-deposit-company="'
            + escape(adviser_setup['company_name'], quote=True)
            + '" data-deposit-token="'
            + adviser_setup['offer_id']
            + '"'
            if adviser_setup
            else ''
        )
        + '>'
    )
    with translation.override(selected_language(request)):
        context = {
            'signed_in': bool(person or adviser_setup),
            'albert_import': False,
            **extra_context,
        }
        if person and template == 'import.html':
            from .profile import page_context

            context.update(page_context(person))
        body = get_template('employer/' + template).render(context, request=request)
    return HttpResponse(body.replace('<body>', body_tag))
