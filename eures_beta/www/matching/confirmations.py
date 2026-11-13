"""Local candidate dialogue: one explicit question at a time, no external call."""

from functools import wraps
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.contrib.auth.views import redirect_to_login
from eures_beta.www.accounts.views import selected_language
from eures_beta.candidates.forms import FORMS, SCHEDULE_DAYS, SCHEDULE_PERIODS
from eures_beta.candidates.occupation_choices import resolve_reference
from eures_beta.skills.skills_pilot import catalogue
from eures_beta.matching import (
    access,
    confirmation_services as service,
    dialogue_services,
)
from eures_beta.matching.services import StaleEvaluation

LABELS = {
    'skill': _('Declared skill'),
    'skills': _('Declared skills'),
    'language': _('Language level'),
    'languages': _('Languages'),
    'mobility': _('Workplace and mobility'),
    'availability': _('Start date'),
    'schedule': _('Required time slots'),
    'permit': _('Required authorisation'),
    'permits': _('Driving licences and authorisations'),
    'work_condition': _('Working condition'),
    'work_conditions': _('Working conditions'),
    'contract': _('Contract'),
    'salary': _('Salary'),
    'working_time': _('Working time'),
}
ANSWERS = [
    ('yes', _('Yes, this is still correct for this offer')),
    ('conditional', _('Yes, under conditions')),
    ('no', _('No, for this offer')),
    ('changed', _('My situation has changed in general')),
    ('clarify', _('I need more information')),
]


class AnswerForm(forms.Form):
    key = forms.CharField(max_length=250, widget=forms.HiddenInput)
    fingerprint = forms.CharField(max_length=64, widget=forms.HiddenInput)
    previous = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    value = forms.ChoiceField(
        label=_('Your answer'), choices=ANSWERS, widget=forms.RadioSelect
    )
    detail = forms.CharField(
        label=_('Conditions, correction or information needed'),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=_(
            'Describe work-related details only. Do not include sensitive personal information.'
        ),
    )

    def clean(self):
        data = super().clean()
        if data.get('value') in ('conditional', 'changed', 'clarify') and not data.get(
            'detail'
        ):
            self.add_error('detail', _('Please specify your answer.'))
        return data


class AgreementForm(forms.Form):
    previous = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    fingerprint = forms.CharField(max_length=64, widget=forms.HiddenInput)
    agreed = forms.ChoiceField(
        label=_(
            'Separate permission to share my profile with this employer for this offer'
        ),
        choices=[
            ('yes', _('I agree to this transmission')),
            ('no', _('I do not agree to this transmission')),
        ],
        widget=forms.RadioSelect,
    )


def destination(pk, language):
    return reverse('candidate_offer_confirmation', args=[pk]) + '?lang=' + language


def entry_candidate(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        with translation.override(selected_language(request)):
            return view(request, *args, **kwargs)

    return wrapped


@never_cache
@require_http_methods(['POST'])
def invite(request, pk):
    try:
        service.request_confirmation(request.user, pk)
    except ObjectDoesNotExist:
        raise Http404
    return redirect(
        reverse('matching_detail', args=[pk]) + '?lang=' + selected_language(request)
    )


def display_rows(rows, language):
    cards, skills = catalogue()
    days, periods = dict(SCHEDULE_DAYS), dict(SCHEDULE_PERIODS)
    forms = [
        cls(**({'language': language} if step == 1 else {}))
        for step, cls in FORMS.items()
        if step < 4
    ]
    fields = {name: field for form in forms for name, field in form.fields.items()}

    def text(value):
        if value in (None, '', [], {}):
            return str(_('Not specified'))
        if isinstance(value, bool):
            return str(_('Yes') if value else _('No'))
        if isinstance(value, list):
            return ', '.join(text(item) for item in value)
        return str(value)

    def skill_label(uri):
        return skills.get(uri, {}).get('labels', {}).get(language) or str(
            _('Skill reference needs clarification')
        )

    def declared(name, value):
        if name in ('acquired_skills', 'learning_activities'):
            return ', '.join(skill_label(uri) for uri in value or []) or str(
                _('Not specified')
            )
        if name == 'occupation_skills':
            from eures_beta.skills.continuous import summary

            return summary(value, language) or str(_('Not specified'))
        if name == 'language_skills':
            return ', '.join(
                item['code'].upper() + ' ' + item['level']
                for item in (value or {}).get('languages', [])
            ) or str(_('Not specified'))
        choices = dict(getattr(fields.get(name), 'choices', []))
        if isinstance(value, list):
            return ', '.join(str(choices.get(item, item)) for item in value) or str(
                _('Not specified')
            )
        return text(choices.get(value, value))

    for row in rows:
        row['label'] = LABELS[row['kind']]
        row['declared'] = [
            (fields[name].label, declared(name, value))
            for name, value in row['presented']['declared'].items()
            if name in fields
        ]
        expected = row['presented']['expected']
        kind = row['kind']
        if kind == 'skill':
            expected = skill_label(expected)
        elif kind == 'contract':
            from eures_beta.www.employer.workspace import OfferEditForm

            expected = dict(OfferEditForm.base_fields['contractType'].choices).get(
                expected, expected
            )
        elif kind == 'work_condition':
            expected = dict(fields['working_conditions'].choices).get(
                expected, expected
            )
        elif kind == 'schedule':
            parts = [
                str(days[day]) + ' — ' + str(periods[period])
                for slot in expected['slots']
                for day, period in [slot.split(':')]
            ]
            parts.append(expected['text'])
            expected = ' · '.join(str(part) for part in parts if part)
        elif kind == 'availability':
            expected = ' · '.join(
                str(part)
                for part in (
                    (
                        (str(_('Latest start date')) + ': ' + expected['latest_start'])
                        if expected['latest_start']
                        else ''
                    ),
                    expected['text'],
                )
                if part
            )
        elif kind == 'mobility':
            countries = dict(fields['desired_countries'].choices)
            expected = ' · '.join(
                str(part)
                for part in (
                    countries.get(expected['country'], expected['country']),
                    expected['city'],
                    expected['commute'],
                )
                if part
            )
        elif kind == 'salary':
            salary = expected['structured']
            parts = [expected['text']]
            if salary:
                parts.append(
                    ' '.join(
                        [
                            str(_('Maximum')),
                            str(salary['maximum']),
                            salary['currency'],
                            str(
                                dict(fields['salary_period'].choices).get(
                                    salary['period'], salary['period']
                                )
                            ),
                            str(
                                dict(fields['salary_basis'].choices).get(
                                    salary['basis'], salary['basis']
                                )
                            ),
                        ]
                    )
                )
            expected = ' · '.join(parts).strip(' ·')
        elif kind == 'language':
            expected = expected['code'].upper() + ' ' + expected['level']
        row['expected'] = text(expected)
        row['answer_label'] = (
            dict(ANSWERS).get(row['answer'].value)
            if row['answer']
            else _('Awaiting confirmation')
        )
    return rows


@entry_candidate
@require_http_methods(['GET'])
def inbox(request):
    from eures_beta.www.matching.conversations import listed

    return render(
        request,
        'matching/confirmation_inbox.html',
        dict(
            entries=service.candidate_requests(request.user).select_related(
                'pair__offer', 'pair'
            ),
            albert_available=dialogue_services.enabled(),
            shared_conversations=listed(request.user),
            page_language=selected_language(request),
        ),
    )


@entry_candidate
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def dialogue(request, pk):
    obj = get_object_or_404(
        service.candidate_requests(request.user).select_related(
            'pair__candidate', 'pair__offer'
        ),
        pk=pk,
    )
    language = selected_language(request)
    state = service.review(obj)
    error, status = '', 200
    action = request.POST.get('action') if request.method == 'POST' else None
    form = AnswerForm(request.POST if action == 'answer' else None)
    agreement_form = AgreementForm(
        request.POST if action == 'agree' else None,
        initial={
            'fingerprint': state['fingerprint'],
            'previous': obj.agreements.order_by('-pk')
            .values_list('pk', flat=True)
            .first()
            or 0,
        },
    )
    if request.method == 'POST':
        try:
            if action == 'answer' and form.is_valid():
                service.answer(request.user, obj.pk, **form.cleaned_data)
                return redirect(destination(pk, language))
            if action == 'agree' and agreement_form.is_valid():
                service.agree(
                    request.user,
                    pk,
                    agreement_form.cleaned_data['fingerprint'],
                    agreement_form.cleaned_data['agreed'] == 'yes',
                    previous=agreement_form.cleaned_data['previous'],
                )
                return redirect(destination(pk, language))
            status = 400
        except StaleEvaluation:
            error, status = (
                _(
                    'The offer, profile or answers changed. Review the current information before confirming.'
                ),
                409,
            )
        except ObjectDoesNotExist:
            raise Http404
        except ValueError:
            error, status = (
                _('Review the conditions before recording your answer.'),
                400,
            )
    rows = display_rows(state['rows'], language)
    key = request.GET.get('question')
    current = (
        next((row for row in rows if row['key'] == key and row['askable']), None)
        if key
        else state['pending']
    )
    if current and action != 'answer':
        latest = obj.answers.filter(question_key=current['key']).order_by('-pk').first()
        form = AnswerForm(
            initial={
                'key': current['key'],
                'fingerprint': current['fingerprint'],
                'previous': latest.pk if latest else 0,
                'value': current['answer'].value if current.get('answer') else None,
                'detail': current['answer'].detail if current.get('answer') else '',
            }
        )
    return render(
        request,
        'matching/confirmation_dialogue.html',
        dict(
            obj=obj,
            state=state,
            rows=rows,
            current=current,
            form=form,
            agreement_form=agreement_form,
            error_forms=(form, agreement_form),
            simulated_dialogue=dialogue_services.enabled(),
            live_dialogue=dialogue_services.live(),
            page_language=language,
            error=error,
        ),
        status=status,
    )
