"""Explicitly opt-in loopback email authentication rehearsal; with explicit company ownership."""
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

from .models import EmployerEmailLink, EmployerIdentity, EmployerCompany, EmployerMembership, EmployerImport
from .employer_ownership import identity, memberships


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
    pending_id = request.session.get('employer_pending_import')
    pending = EmployerImport.objects.filter(pk=pending_id, company__isnull=True,
                session_key=request.session.session_key).first() if pending_id else None
    form = EmailForm(request.POST if request.method == 'POST' else None,
                     initial={'email': pending.email} if pending else None)
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
            EmployerEmailLink.objects.create(email=email, pending_import=pending, digest=hashlib.sha256(raw.encode()).hexdigest(),
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
        person, _ = EmployerIdentity.objects.get_or_create(email=link.email)
        request.session.cycle_key()
        request.session['employer_identity_id'] = person.pk
        # Only the draft explicitly carried by this single-use link can be attached.
        request.session.pop('employer_pending_import', None)
        if link.pending_import_id:
            draft = EmployerImport.objects.select_for_update().filter(pk=link.pending_import_id,
                                                                      company__isnull=True).first()
            if draft and draft.created_by_id in (None, person.pk):
                draft.created_by = person
                draft.session_key = ''
                draft.save(update_fields=['created_by', 'session_key', 'updated'])
                request.session['employer_claim_import'] = str(draft.pk)
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
    person = identity(request)
    if not person:
        return redirect('employer_access')
    pending = EmployerImport.objects.filter(company__isnull=True, created_by=person).order_by('-created')
    requested = request.session.get('employer_claim_import')
    draft = (pending.filter(pk=requested).first() if requested else None) or pending.first()
    if draft:
        request.session['employer_claim_import'] = str(draft.pk)
    else:
        request.session.pop('employer_claim_import', None)
    return page(request, 'connected', email=email,
                companies=EmployerCompany.objects.filter(memberships__in=memberships(request)),
                pending_import=request.session.get('employer_claim_import'),
                pending_title=(draft.data.get('title') or draft.data.get('description', '')[:125]) if draft else '',
                attached=request.session.pop('employer_attached', False))


@enabled
@require_POST
def sign_out(request):
    request.session.flush()
    return redirect('employer_access')


@enabled
@require_POST
def attach(request):
    """Attach only the draft proven by the consumed login link, with explicit workspace choice."""
    person = identity(request)
    pending_id = request.session.get('employer_claim_import')
    if not person or not pending_id:
        raise Http404
    with transaction.atomic():
        draft = EmployerImport.objects.select_for_update().filter(pk=pending_id, company__isnull=True, created_by=person).first()
        if draft is None:
            raise Http404
        company_id = request.POST.get('company', '')
        if company_id:
            if not company_id.isdecimal():
                raise Http404
            member = memberships(request).select_for_update().filter(company_id=company_id).first()
            if not member:
                raise Http404
            company = member.company
        else:
            name = request.POST.get('name', '').strip()
            if not name or len(name) > 100:
                return redirect('employer_connected')
            company = EmployerCompany.objects.create(name=name)
            EmployerMembership.objects.create(person=person, company=company)
        draft.company = company
        draft.created_by = person
        # Session ownership must no longer provide an alternative access path.
        draft.session_key = ''
        draft.save(update_fields=['company', 'created_by', 'session_key', 'updated'])
    request.session.pop('employer_claim_import', None)
    request.session['employer_attached'] = company.name
    return redirect('employer_connected')
