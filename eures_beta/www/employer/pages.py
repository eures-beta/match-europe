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


def render_page(request, template):
    person = identity(request)
    body_tag = (
        '<body data-employer-api="true" data-employer-connected="'
        + ('true' if person else 'false')
        + '"'
        + (
            ' data-employer-email="' + escape(person.email, quote=True) + '"'
            if person
            else ''
        )
        + '>'
    )
    with translation.override(selected_language(request)):
        context = {
            'signed_in': bool(person),
            'albert_import': False,
        }
        if person and template == 'import.html':
            from .response_practice import page_context

            context.update(page_context(person))
        body = get_template('employer/' + template).render(context, request=request)
    return HttpResponse(body.replace('<body>', body_tag))
