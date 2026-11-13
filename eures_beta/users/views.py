"""Closed, passwordless sign-in using django-sesame, not a signup endpoint."""

import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from sesame.utils import get_query_string, get_user

from .forms import AdviserSignatureForm, LoginForm
from .models import User
from eures_beta.invitations.eligibility import has_candidate_invitation
from eures_beta.emails.backend import real_email_allowed
from .rate_limits import allow_request
from .login_return import remember, consume, IMPORT_PATHS

logger = logging.getLogger(__name__)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def account(request):
    language = selected_language(request)
    with translation.override(language):
        if request.user.kind != User.Kind.ADVISER:
            if request.method == 'POST':
                return HttpResponseNotAllowed(['GET'])
            return render(request, 'users/account.html')

        form = AdviserSignatureForm(
            request.POST if request.method == 'POST' else None,
            instance=request.user,
        )
        if form.is_valid():
            form.save(commit=False).save(update_fields=form.Meta.fields)
            messages.success(request, _('Your email signature has been saved.'))
            return redirect(reverse('account', query={'lang': language}))
        return render(request, 'users/account.html', {'signature_form': form})


@never_cache
@login_required
@require_GET
def dashboard(request):
    with translation.override(selected_language(request)):
        if request.user.kind == 'adviser':
            from eures_beta.invitations.adviser import invitations_tab
            from eures_beta.invitations.views import adviser_dashboard

            if request.GET.get('tab') == 'employers':
                return adviser_dashboard(request)
            return invitations_tab(request)
        if request.user.kind == 'candidate':
            if hasattr(request.user, 'candidate_profile'):
                return redirect('candidate_profile')
            if has_candidate_invitation(request.user):
                return redirect('candidate_prepare')
            return render(request, 'users/dashboard.html')
        from eures_beta.employers.dashboard import employer_dashboard

        return employer_dashboard(request)


def email_ready():
    origin = urlsplit(settings.LOGIN_EMAIL_ORIGIN)
    return bool(
        real_email_allowed()
        and settings.LOGIN_EMAIL_ENABLED
        and origin.scheme == 'https'
        and origin.hostname in settings.ALLOWED_HOSTS
        and not origin.username
        and not origin.password
        and origin.path in ('', '/')
        and not origin.query
        and not origin.fragment
        and settings.EMAIL_HOST
        and settings.DEFAULT_FROM_EMAIL
    )


def selected_language(request):
    language = request.GET.get(
        'lang', request.session.get('login_language', request.LANGUAGE_CODE)
    )
    return language if language in ('fr', 'en', 'de') else 'fr'


def page(request, stage, **context):
    language = selected_language(request)
    request.session['login_language'] = language
    with translation.override(language):
        response = render(request, 'users/login.html', {'stage': stage, **context})
    # The URL is already clean here. Keep same-site Origin/Referer for HTTPS
    # CSRF checks; no-referrer documents make browsers submit Origin: null.
    response['Referrer-Policy'] = 'same-origin'
    return response


@never_cache
@sensitive_post_parameters('email')
@require_http_methods(['GET', 'POST'])
def login(request):
    remember(request)
    if request.user.is_authenticated:
        return redirect(consume(request, settings.LOGIN_REDIRECT_URL))
    with translation.override(selected_language(request)):
        form = LoginForm(request.POST if request.method == 'POST' else None)
        valid = request.method == 'POST' and form.is_valid()
    ready = email_ready()
    if valid:
        if not ready:
            # Transport configuration must not change the previewed login journey.
            # Keep sending disabled, without exposing links or account existence.
            return page(request, 'sent', email_ready=False)
        email = form.cleaned_data['email'].strip().lower()
        if allow_request(request, email):
            user = (
                get_user_model()
                .objects.filter(email__iexact=email, is_active=True)
                .first()
            )
            if user:
                language = selected_language(request)
                link = (
                    settings.LOGIN_EMAIL_ORIGIN.rstrip('/')
                    + reverse('magic_confirm')
                    + get_query_string(user)
                )
                destination = request.session.get('login_return_path', '')
                if destination in IMPORT_PATHS:
                    from urllib.parse import urlencode

                    link += '&' + urlencode({'next': destination})
                with translation.override(language):
                    body = render_to_string('users/login_email.txt', {'link': link})
                    try:
                        send_mail(
                            _('Your Match Europe sign-in link'),
                            body,
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email],
                        )
                    except Exception:
                        # No exception payload: SMTP exceptions may contain recipients.
                        logger.error(
                            'Magic-link email delivery failed; inspect the mail service privately.'
                        )
        return page(request, 'sent', email_ready=ready)
    return page(request, 'login', form=form, email_ready=ready)


@never_cache
@require_http_methods(['GET', 'POST'])
def confirm(request):
    if request.method == 'GET':
        remember(request)
        if 'sesame' in request.GET:
            # Do not consume on GET: mail scanners must not log the user in.
            token = request.GET['sesame']
            request.session.pop('magic_login_token', None)
            if len(token) <= 256:
                request.session['magic_login_token'] = token
            response = redirect('magic_confirm')
            response['Referrer-Policy'] = 'no-referrer'
            return response
        return page(
            request,
            'confirm' if request.session.get('magic_login_token') else 'invalid',
        )
    language = selected_language(request)
    token = request.session.pop('magic_login_token', '')
    user = get_user(token, update_last_login=False) if token else None
    if user is None:
        return page(request, 'invalid')
    destination = consume(request, settings.LOGIN_REDIRECT_URL)
    with transaction.atomic():
        # Serialise token consumption with other logins for the same account.
        if not get_user_model().objects.select_for_update().filter(pk=user.pk).exists():
            return page(request, 'invalid')
        user = get_user(token, update_last_login=False)
        if user is None:
            return page(request, 'invalid')
        auth_login(request, user)
        # Switching accounts flushes the old session; retain the chosen language.
        request.session['login_language'] = language
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    return redirect(destination)


@never_cache
@require_POST
def logout(request):
    destination = request.GET.get('next', '')
    auth_logout(request)
    if destination in IMPORT_PATHS:
        from urllib.parse import urlencode

        return redirect(
            reverse('magic_login')
            + '?'
            + urlencode(
                {
                    'next': destination,
                    'lang': destination.rsplit('-', 1)[-1].removesuffix('.html'),
                }
            )
        )
    return redirect('home')


@require_GET
def admin_login(request):
    # Staff use the same email link. Admin permissions are still enforced by Django.
    return redirect('magic_login')


def password_disabled(request, **kwargs):
    raise Http404
