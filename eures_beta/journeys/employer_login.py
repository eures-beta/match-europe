"""Explicitly opt-in loopback email authentication rehearsal; grants no business rights."""
import hashlib
import os
import secrets
from datetime import timedelta
from functools import wraps

from django import forms
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods, require_GET

from .models import EmployerEmailLink


def enabled(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if (not settings.DEMO_MODE or os.environ.get('ME_EMPLOYER_EMAIL_LOCAL') != '1'
                or request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1')):
            raise Http404
        return view(request, *args, **kwargs)
    return wrapped


class EmailForm(forms.Form):
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))


def page(request, stage, **context):
    lang = request.GET.get('lang', request.session.get('employer_auth_language', translation.get_language() or 'fr'))
    lang = lang if lang in ('fr', 'en', 'de') else 'fr'
    request.session['employer_auth_language'] = lang
    with translation.override(lang):
        return render(request, 'employer_login.html', {'stage': stage, 'auth_shell': f'employer_auth_shell_{lang}.html', **context})


@enabled
@require_http_methods(["GET", "POST"])
def access(request):
    form = EmailForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        now = timezone.now()
        email = form.cleaned_data['email'].lower()
        # Limit by browser as well as address, including across separate sessions.
        recent = EmployerEmailLink.objects.filter(email=email, created__gt=now-timedelta(minutes=15))
        if now.timestamp()-request.session.get('employer_email_sent_at', 0) < 60 or recent.count() >= 5:
            return page(request, 'limited', form=form)
        raw = secrets.token_urlsafe(32)
        with transaction.atomic():
            EmployerEmailLink.objects.filter(email=email, used=False).update(used=True)
            EmployerEmailLink.objects.create(email=email, digest=hashlib.sha256(raw.encode()).hexdigest(),
                                             expires=now+timedelta(minutes=15))
        request.session['employer_email_sent_at'] = now.timestamp()
        # Rehearsal delivery: message is isolated to the requesting browser's server-side session.
        request.session['employer_test_message'] = {'email': email, 'link': reverse('employer_confirm', args=[raw])}
        return redirect('employer_email_sent')
    return page(request, 'access', form=form)


@enabled
@require_GET
def sent(request):
    return page(request, 'sent')


@enabled
@require_GET
def inbox(request):
    return page(request, 'inbox', message=request.session.get('employer_test_message'))


@enabled
@require_http_methods(["GET", "POST"])
def confirm(request, token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    if request.method != 'POST':
        valid = EmployerEmailLink.objects.filter(digest=digest, used=False, expires__gt=timezone.now()).exists()
        return page(request, 'confirm' if valid else 'invalid')
    with transaction.atomic():
        link = EmployerEmailLink.objects.select_for_update().filter(digest=digest, used=False,
                                                                   expires__gt=timezone.now()).first()
        if not link:
            return page(request, 'invalid')
        link.used = True
        link.save(update_fields=['used'])
        request.session.cycle_key()
        request.session['employer_verified_email'] = link.email
        request.session.set_expiry(3600)
        request.session.pop('employer_test_message', None)
    return redirect('employer_connected')


@enabled
@require_GET
def connected(request):
    email = request.session.get('employer_verified_email')
    if not email:
        return redirect('employer_access')
    return page(request, 'connected', email=email)


@enabled
@require_POST
def sign_out(request):
    request.session.flush()
    return redirect('employer_access')
