from eures_beta.invitations.eligibility import has_candidate_invitation

"""Guided candidate project rehearsal without CV or career-history collection."""

import secrets
import time
from django import forms
from decimal import Decimal
from datetime import date
from django.http import HttpResponseBadRequest, JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.debug import sensitive_post_parameters
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from eures_beta.candidates.schedule_rules import suggested_conditions
from eures_beta.candidates.language_choices import upgrade_language_answers
from eures_beta.candidates.occupation_choices import resolve_reference
from eures_beta.candidates import skill_choices
from eures_beta.skills.continuous import trial_request as continuous_trial_request
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from eures_beta.candidates.forms import (
    KEY,
    TTL,
    TTL_WARNING,
    CONDITIONALLY_REQUIRED,
    ProjectForm,
    SCHEDULE_DAYS,
    FORMS,
    TITLES,
    SCHEMA,
)


@never_cache
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def journey(request):
    language = request.GET.get('lang', request.LANGUAGE_CODE)
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    with translation.override(language):
        return workflow(request, language)


def workflow(request, language):
    from eures_beta.candidates import registration

    def go(step):
        return redirect(f'/candidate/prepare/?step={step}&lang={language}')

    draft = request.session.get(KEY)
    if draft and 'owner_id' in draft and draft['owner_id'] != request.user.pk:
        request.session.pop(KEY, None)
        draft = None
    now = time.time()
    last_activity = (draft or {}).get('touched_at', (draft or {}).get('created_at', 0))
    expired = bool(draft and not 0 <= now - last_activity < TTL)
    if expired:
        request.session.pop(KEY, None)
        draft = None
    if draft:
        upgrade_language_answers(draft['data'])
        draft['touched_at'] = now
        request.session[KEY] = draft
    if draft and draft.get('schema') != SCHEMA:
        # Keep project answers, discard all removed career/CV fields and invalidate old forms.
        allowed = {
            name for form_class in FORMS.values() for name in form_class().fields
        }
        draft = {
            'schema': SCHEMA,
            'created_at': draft['created_at'],
            'token': secrets.token_urlsafe(24),
            'data': {
                name: value
                for name, value in draft.get('data', {}).items()
                if name in allowed or name == 'language_notes'
            },
            'unlocked': 1,
        }
        request.session[KEY] = draft
        return go(1)
    try:
        step = int(request.GET.get('step', 1))
    except (ValueError, TypeError):
        return HttpResponseBadRequest()
    if step not in FORMS:
        return HttpResponseBadRequest()
    action = request.POST.get('action') if request.method == 'POST' else None
    if request.method == 'POST' and 'target_language' in request.POST:
        if step != 1 or request.POST['target_language'] not in ('fr', 'en', 'de'):
            return HttpResponseBadRequest()
        action = 'language'
    if action == 'extend':
        if not draft:
            return JsonResponse({'extended': False}, status=409)
        if request.FILES or not secrets.compare_digest(
            request.POST.get('token', ''), draft['token']
        ):
            return HttpResponseBadRequest()
        return JsonResponse({'extended': True, 'seconds': TTL})
    if not draft:
        if request.method == 'POST':
            return go(1)
        draft = {
            'schema': SCHEMA,
            'created_at': now,
            'touched_at': now,
            'token': secrets.token_urlsafe(24),
            'data': {},
            'unlocked': 1,
        }
        request.session[KEY] = draft
    if request.method == 'GET' and 'without_cv' in request.GET:
        return go(1)
    if step > draft['unlocked']:
        return go(draft['unlocked'])
    if request.method == 'POST':
        if request.FILES or not secrets.compare_digest(
            request.POST.get('token', ''), draft['token']
        ):
            return HttpResponseBadRequest()
        if action == 'discard':
            request.session.pop(KEY, None)
            return redirect('/candidate/?lang=' + language)
        allowed_actions = (
            ('search', 'continue', 'language')
            if step == 1
            else ('finish',) if step == 4 else ('continue',)
        )
        if action not in allowed_actions:
            return HttpResponseBadRequest()
    form_class = FORMS[step]
    initial = draft['data']
    invited_candidate = (
        request.user.is_authenticated
        and has_candidate_invitation(request.user)
        and not hasattr(request.user, 'candidate_profile')
    )
    if step == 4 and invited_candidate:
        initial = {**initial, 'contact_email': request.user.email}
    if step == 4 and draft.get('editing_user'):
        if (
            not request.user.is_authenticated
            or request.user.pk != draft['editing_user']
        ):
            raise PermissionDenied
        initial = {**initial, 'contact_email': request.user.email}
    form = form_class(
        request.POST if request.method == 'POST' else None,
        initial=initial,
        **(
            {'language': language, 'partial': action == 'language'} if step == 1 else {}
        ),
    )
    if step == 4 and (draft.get('editing_user') or invited_candidate):
        form.fields['contact_email'].disabled = True
        form.fields['contact_email'].label = _('Email address')
    if action == 'language' and form.is_valid():
        # Keep incomplete choices across languages without unlocking registration.
        complete = ProjectForm(form.cleaned_data, language=language)
        if not complete.is_valid():
            draft['unlocked'] = 1
        draft['data'].update(form.cleaned_data)
        request.session[KEY] = draft
        return redirect(
            f"/candidate/prepare/?step=1&lang={request.POST['target_language']}"
        )
    if (
        request.method == 'POST'
        and action not in ('search', 'language')
        and form.is_valid()
    ):
        draft['data'].update(
            {
                name: str(value) if isinstance(value, (Decimal, date)) else value
                for name, value in form.cleaned_data.items()
                if name != 'reviewed'
            }
        )
        if (
            step == 2
            and form.cleaned_data['language_skills']['status'] != 'unspecified'
        ):
            draft['data'].pop('language_notes', None)
        if step == 4:
            if draft.get('editing_user'):
                try:
                    registration.update_profile(
                        request.user,
                        draft['data'],
                        language,
                        expected_updated_at=draft.get('source_profile_updated_at'),
                    )
                except registration.StaleProfile:
                    return render(
                        request,
                        'matching/dialogue_profile_conflict.html',
                        {'page_language': language},
                        status=409,
                    )
                destination = 'candidate_profile'
            elif invited_candidate:
                from django.utils import timezone

                registration.create_verified_profile(
                    request.user, draft['data'], language, timezone.now()
                )
                request.session.pop(KEY, None)
                return redirect('candidate_profile')
            else:
                from eures_beta.users.rate_limits import allow_request

                if allow_request(request, form.cleaned_data['contact_email']):
                    try:
                        pending = registration.create_request(
                            form.cleaned_data['contact_email'], draft['data'], language
                        )
                    except IntegrityError:
                        # A simultaneous request for this address has the same generic outcome.
                        pass
                    else:
                        registration.send_confirmation(pending)
                destination = 'candidate_registration_requested'
            if draft.get('editing_user'):
                request.session.pop(KEY, None)
            else:
                # Keep the original browser draft while the email is being verified.
                request.session[KEY] = draft
            return redirect(destination)
        draft['unlocked'] = max(draft['unlocked'], min(step + 1, 4))
        request.session[KEY] = draft
        if (
            step < 4
            and draft['unlocked'] >= 4
            and request.POST.get('return') == 'review'
        ):
            return go(4)
        return go(min(step + 1, 4))
    if action == 'search':
        form.errors.clear()
    summary = []
    if step == 4:
        for number in (1, 2, 3):
            fields = []
            review_form = FORMS[number](
                **({'language': language} if number == 1 else {})
            )
            for name, field in review_form.fields.items():
                value = draft['data'].get(name, '')
                if name in (
                    'occupation_query',
                    'skill_catalogue_version',
                    'condition_overrides',
                    'auto_conditions',
                ):
                    continue
                if (
                    name in skill_choices.FIELDS
                    and draft['data'].get('project_mode') != 'open'
                ):
                    continue
                if (
                    name in ('occupation_references', 'desired_occupations')
                    and draft['data'].get('project_mode') == 'open'
                ):
                    continue
                if (
                    name == 'schedule_strict'
                    and draft['data'].get('schedule_preference') != 'specific'
                ):
                    continue
                if (
                    name.startswith('schedule_')
                    and name != 'schedule_preference'
                    and draft['data'].get('schedule_preference') != 'specific'
                ):
                    continue
                if name in (
                    'commute_time',
                    'transport_modes',
                    'transport_details',
                ) and draft['data'].get('mobility') not in ('commute', 'both'):
                    continue
                conditional = {
                    'available_from': ('availability', 'date'),
                    'contract_details': ('contract_types', 'other'),
                    'licence_details': ('licences_held', 'other'),
                    'transport_details': ('transport_modes', 'other'),
                    **{
                        key: ('salary_preference', 'minimum')
                        for key in (
                            'salary_amount',
                            'salary_currency',
                            'salary_period',
                            'salary_basis',
                        )
                    },
                }
                if name in conditional:
                    parent, expected = conditional[name]
                    parent_value = draft['data'].get(parent, [])
                    if not (
                        expected in parent_value
                        if isinstance(parent_value, list)
                        else parent_value == expected
                    ):
                        continue
                if name == 'occupation_references':
                    value = '\n'.join(
                        row['label']
                        for item in value
                        if (row := resolve_reference(item, language))
                    )
                elif name == 'occupation_skills':
                    from eures_beta.skills.continuous import summary as skills_summary

                    value = skills_summary(value, language)
                    if not value:
                        continue
                elif isinstance(field, forms.MultipleChoiceField):
                    value = '\n'.join(
                        str(dict(field.choices).get(item, item)) for item in value
                    )
                elif isinstance(field, forms.BooleanField):
                    value = _('Yes') if value else _('No')
                elif isinstance(field, forms.ChoiceField) and value:
                    value = dict(field.choices).get(value, value)
                fields.append((name, field.label, value))
            summary.append({'step': number, 'title': TITLES[number], 'fields': fields})
    error_summary = []
    if form.is_bound and action != 'search':
        # Same order as the fields on the page, form-wide errors first.
        order = ['__all__', *form.fields]
        for name, messages in sorted(
            form.errors.items(), key=lambda item: order.index(item[0])
        ):
            if name == '__all__':
                error_summary += [
                    {'label': '', 'message': m, 'anchor': ''} for m in messages
                ]
                continue
            bound = form[name]
            widget = bound.field.widget
            if name in skill_choices.FIELDS:
                anchor = 'section_' + name
            elif name == 'occupation_references':
                anchor = 'id_occupation_query'
            elif name == 'language_skills':
                anchor = 'candidate-language-field'
            elif getattr(widget, 'allow_multiple_selected', False) or (
                getattr(widget, 'input_type', None) == 'radio'
            ):
                anchor = bound.auto_id + '_0'
            else:
                anchor = bound.auto_id
            error_summary += [
                {'label': bound.label, 'message': m, 'anchor': anchor} for m in messages
            ]
    return_to_review = (
        step < 4
        and draft['unlocked'] >= 4
        and (request.GET.get('return') or request.POST.get('return')) == 'review'
    )
    return render(
        request,
        'candidates/journey.html',
        {
            'form': form,
            'invited_candidate': invited_candidate,
            'continuous_skills': continuous_trial_request(request),
            'skill_sections': (
                skill_choices.sections(form, language) if step == 1 else []
            ),
            'skill_field_names': skill_choices.FIELDS,
            'error_summary': error_summary,
            'return_to_review': return_to_review,
            'conditionally_required': CONDITIONALLY_REQUIRED,
            'draft_seconds': TTL,
            'draft_warning_seconds': TTL_WARNING,
            'schedule_suggestions': (
                suggested_conditions(
                    form.cleaned_data
                    if form.is_bound and hasattr(form, 'cleaned_data')
                    else draft['data']
                )
                if step == 3
                else []
            ),
            'language_declaration': draft['data'].get('language_skills', {}),
            'language_notes': draft['data'].get('language_notes', []),
            'step': step,
            'title': TITLES[step],
            'previous': max(step - 1, 1),
            'draft': draft,
            'expired': expired,
            'summary': summary,
            'schedule_fields': (
                [form['schedule_' + day] for day, label in SCHEDULE_DAYS]
                if step == 3
                else []
            ),
            'reference_rows': getattr(form, 'reference_rows', []),
            'search_performed': bool(
                step == 1
                and (action == 'search' or request.POST.get('occupation_query'))
            ),
            'steps': [
                {
                    'number': number,
                    'title': title,
                    'available': number <= draft['unlocked'],
                }
                for number, title in TITLES.items()
            ],
        },
    )
