"""Browser confirmation uses a clean URL, CSRF and a one-time POST."""

import secrets
import time
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.cache import never_cache
from eures_beta.users.models import User
from eures_beta.users.views import selected_language, email_ready
from . import registration
from .models import CandidateProfile
from .skill_choices import FIELDS


def page(request, stage, **context):
    with translation.override(selected_language(request)):
        response = render(
            request, 'candidates/registration.html', {'stage': stage, **context}
        )
    response['Referrer-Policy'] = 'same-origin'
    return response


@never_cache
@require_GET
def requested(request):
    from eures_beta.occupations.continuous import trial_request

    return page(
        request,
        'requested',
        email_delivery_available=email_ready(),
        local_confirmation_available=bool(
            trial_request(request)
            and request.session.get('candidate_local_preview_token')
        ),
    )


@never_cache
@require_http_methods(['POST'])
def local_confirmation(request):
    from eures_beta.occupations.continuous import trial_request

    if not trial_request(request):
        raise Http404
    token = request.session.pop('candidate_local_preview_token', '')
    pending = registration.find_registration(token) if token else None
    if not pending or not pending.email.endswith('.invalid'):
        raise Http404
    request.session['candidate_confirmation_token'] = token
    request.session['login_language'] = pending.language
    return redirect('candidate_registration_confirm')


@never_cache
@require_http_methods(['GET', 'POST'])
def confirm(request):
    key = 'candidate_confirmation_token'
    if request.method == 'GET':
        if 'token' in request.GET:
            token = request.GET['token']
            request.session.pop(key, None)
            pending = (
                registration.find_registration(token) if len(token) <= 512 else None
            )
            if pending:
                request.session[key] = token
                request.session['login_language'] = pending.language
            response = redirect('candidate_registration_confirm')
            response['Referrer-Policy'] = 'no-referrer'
            return response
        pending = (
            registration.find_registration(request.session[key])
            if request.session.get(key)
            else None
        )
        return page(
            request,
            'confirm' if pending else 'invalid',
            pending_name=pending.answers.get('display_name', '') if pending else '',
        )
    token = request.session.pop(key, '')
    try:
        # Account, profile and token consumption must all commit or all roll back.
        with transaction.atomic():
            user = registration.confirm_registration(token) if token else None
            if user is None:
                return page(request, 'invalid')
            language = user.candidate_profile.language
            auth_login(request, user, backend='sesame.backends.ModelBackend')
            request.session['login_language'] = language
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    except (IntegrityError, ValidationError):
        return page(request, 'invalid')
    return redirect('candidate_profile')


def owned_profile(request):
    if request.user.kind != User.Kind.CANDIDATE or not request.user.is_active:
        raise PermissionDenied
    profile = CandidateProfile.objects.filter(user=request.user).first()
    if profile is None:
        raise Http404()
    return profile


@never_cache
@login_required
@require_GET
def profile(request):
    obj = owned_profile(request)
    from .journey import FORMS

    groups = []
    with translation.override(selected_language(request)):
        from .journey import TITLES

        answers = registration.profile_answers(obj)
        for step in (1, 2, 3):
            form = FORMS[step](
                initial=answers,
                **({'language': selected_language(request)} if step == 1 else {}),
            )
            rows = []
            for name, field in form.fields.items():
                if name in (
                    'skill_catalogue_version',
                    'occupation_query',
                    'condition_overrides',
                    'auto_conditions',
                ):
                    continue
                if (
                    name.startswith('schedule_')
                    and name != 'schedule_preference'
                    and answers.get('schedule_preference') != 'specific'
                ):
                    continue
                if name in FIELDS and answers.get('project_mode') != 'open':
                    continue
                if (
                    name in ('occupation_references', 'desired_occupations')
                    and answers.get('project_mode') == 'open'
                ):
                    continue
                if name not in answers or answers[name] in ('', None, [], {}):
                    continue
                value = answers[name]
                if name == 'occupation_references':
                    from .occupation_choices import resolve_reference

                    value = '\n'.join(
                        row['label']
                        for item in value
                        if (row := resolve_reference(item, obj.language))
                    )
                elif name == 'occupation_skills':
                    from eures_beta.occupations.continuous import (
                        summary as skills_summary,
                    )

                    value = skills_summary(value, selected_language(request))
                elif name == 'language_skills':
                    value = '\n'.join(
                        row['code'] + ' — ' + row['level']
                        for row in value.get('languages', [])
                    ) or (_('To discuss') if value.get('status') == 'discuss' else '')
                elif isinstance(value, bool):
                    value = _('Yes') if value else _('No')
                elif isinstance(value, list):
                    choices = dict(getattr(field, 'choices', ()))
                    value = '\n'.join(str(choices.get(item, item)) for item in value)
                elif hasattr(field, 'choices'):
                    value = dict(field.choices).get(value, value)
                rows.append((field.label, value))
            groups.append((TITLES[step], rows))
        return render(
            request, 'candidates/profile.html', {'profile': obj, 'groups': groups}
        )


@never_cache
@login_required
@require_http_methods(['POST'])
def edit(request):
    obj = owned_profile(request)
    from .journey import KEY, SCHEMA

    now = time.time()
    request.session[KEY] = {
        'schema': SCHEMA,
        'created_at': now,
        'touched_at': now,
        'token': secrets.token_urlsafe(24),
        'unlocked': 4,
        'editing_user': request.user.pk,
        'data': registration.profile_answers(obj),
    }
    return redirect('/candidate/prepare/?step=4&lang=' + selected_language(request))
