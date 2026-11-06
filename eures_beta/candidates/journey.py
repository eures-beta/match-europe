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
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from .schedule_rules import DERIVED, suggested_conditions, inconsistent_conditions
from .language_choices import LanguageSkillsField, upgrade_language_answers
from .occupation_choices import resolve_reference, search_occupations
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

KEY = 'candidate_journey'
# Inactivity delay: each request on the journey restarts it (WCAG 2.2.1).
TTL = 1800
# The page warns this many seconds before expiry and offers to extend.
TTL_WARNING = 120
# Fields that become mandatory only through a form rule, marked as required.
CONDITIONALLY_REQUIRED = {'occupation_references', 'commute_time', 'transport_modes'}


def text_field(label, required=False, rows=3, help_text=''):
    return forms.CharField(
        label=label,
        required=required,
        max_length=4000,
        help_text=help_text,
        widget=forms.Textarea(attrs={'rows': rows}),
    )


def multiple(label, choices, required=False):
    return forms.MultipleChoiceField(
        label=label,
        choices=choices,
        required=required,
        widget=forms.CheckboxSelectMultiple,
    )


def single(label, choices, required=False):
    return forms.ChoiceField(
        label=label, choices=choices, required=required, widget=forms.RadioSelect
    )


DISCUSS = ('discuss', _('To discuss'))
OTHER = ('other', _('Other'))


class GuidedForm(forms.Form):
    exclusive = {}
    other_details = {}

    def clean(self):
        data = super().clean()
        for name, exclusive in self.exclusive.items():
            values = data.get(name, [])
            if len(values) > 1 and set(values) & set(exclusive):
                self.add_error(
                    name,
                    _('Choose a specific answer or the discussion option, not both.'),
                )
        for name, detail in self.other_details.items():
            if 'other' in data.get(name, []) and not data.get(detail):
                self.add_error(detail, _('Please specify your other choice.'))
        return data


class ProjectForm(GuidedForm):
    occupation_query = forms.CharField(
        label=_('Search for an occupation'),
        max_length=150,
        required=False,
        help_text=_(
            'Job title or ROME/ESCO code. Search, then select one or more results.'
        ),
    )
    occupation_references = multiple(_('Jobs I would like to do'), [])
    desired_occupations = forms.CharField(
        label=_('Another job or a personal job title (optional)'),
        max_length=500,
        required=False,
        help_text=_('Use this if no catalogue result fits. No code will be invented.'),
    )
    desired_countries = multiple(
        _('Countries where I would like to work'),
        [
            ('FR', _('France')),
            ('LU', _('Luxembourg')),
            ('DE', _('Germany')),
            ('BE', _('Belgium')),
            OTHER,
            DISCUSS,
        ],
        True,
    )
    desired_locations = forms.CharField(
        label=_('Regions, towns or another country (optional)'),
        max_length=500,
        required=False,
    )
    exclusive = {'desired_countries': ('discuss',)}
    other_details = {'desired_countries': 'desired_locations'}

    def __init__(self, *args, language='fr', **kwargs):
        super().__init__(*args, **kwargs)
        selected = (
            (
                self.data.getlist('occupation_references')
                if hasattr(self.data, 'getlist')
                else self.data.get('occupation_references', [])
            )
            if self.is_bound
            else self.initial.get('occupation_references', [])
        )
        if not isinstance(selected, list):
            selected = []
        self.reference_rows = [
            row
            for value in selected[:10]
            if (row := resolve_reference(value, language))
        ]
        query = (
            self.data.get('occupation_query', '')
            if self.is_bound
            else self.initial.get('occupation_query', '')
        )
        results = search_occupations(query, language)
        combined = {row['value']: row for row in [*self.reference_rows, *results]}
        self.fields['occupation_references'].choices = [
            (row['value'], row['label']) for row in combined.values()
        ]
        self.reference_rows = list(combined.values())

    def clean(self):
        data = super().clean()
        selected = data.get('occupation_references', [])
        if len(selected) > 10:
            self.add_error('occupation_references', _('Select up to ten occupations.'))
        if not selected and not data.get('desired_occupations'):
            self.add_error(
                'occupation_references',
                _('Select an ESCO or ROME occupation, or enter your own job title.'),
            )
        return data


class MobilityForm(GuidedForm):
    mobility = single(
        _('Your mobility plans'),
        [
            ('commute', _('Commute while keeping my residence')),
            ('move', _('Move for a job')),
            ('both', _('Both are possible')),
            DISCUSS,
        ],
        True,
    )
    commute_time = single(
        _('Maximum one-way commuting time'),
        [
            ('30min', _('30 minutes')),
            ('1h', _('1 hour')),
            ('90min', _('1 hour 30 minutes')),
            ('2h', _('2 hours')),
            ('over2h', _('More than 2 hours')),
            DISCUSS,
        ],
    )
    transport_modes = multiple(
        _('How could you travel to work?'),
        [
            ('car', _('Car')),
            ('train', _('Train')),
            ('bus', _('Bus')),
            ('carpool', _('Carpooling')),
            ('other', _('Other')),
            DISCUSS,
        ],
    )
    transport_details = forms.CharField(
        label=_('Other transport: specify'), max_length=500, required=False
    )
    language_skills = LanguageSkillsField()
    licences_held = multiple(
        _('Which licences or authorisations do you currently hold?'),
        [
            ('B', pgettext_lazy('employer import-v2', 'Licence B')),
            ('C', pgettext_lazy('employer import-v2', 'Licence C')),
            ('CE', pgettext_lazy('employer import-v2', 'Licence CE')),
            ('D', pgettext_lazy('employer import-v2', 'Licence D')),
            ('DE', pgettext_lazy('employer import-v2', 'Licence DE')),
            ('CACES', 'CACES'),
            OTHER,
            ('none', _('None')),
            DISCUSS,
        ],
    )
    licence_details = forms.CharField(
        label=_('Other licence or authorisation: specify'),
        max_length=500,
        required=False,
    )
    exclusive = {'licences_held': ('none', 'discuss'), 'transport_modes': ('discuss',)}
    other_details = {
        'licences_held': 'licence_details',
        'transport_modes': 'transport_details',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound and self.data.get('mobility') not in ('commute', 'both'):
            for name in ('commute_time', 'transport_modes', 'transport_details'):
                self.fields[name].disabled = True
                self.initial[name] = [] if name == 'transport_modes' else ''

    def clean(self):
        data = super().clean()
        if self.data.get('language_discuss') == 'on':
            data['language_skills'] = {'status': 'discuss', 'languages': []}
        if data.get('mobility') in ('commute', 'both'):
            for name in ('commute_time', 'transport_modes'):
                if not data.get(name):
                    self.add_error(
                        name,
                        _('Please choose an answer, or select the discussion option.'),
                    )
        return data


SCHEDULE_DAYS = [
    ('monday', _('Monday')),
    ('tuesday', _('Tuesday')),
    ('wednesday', _('Wednesday')),
    ('thursday', _('Thursday')),
    ('friday', _('Friday')),
    ('saturday', _('Saturday')),
    ('sunday', _('Sunday')),
]
SCHEDULE_PERIODS = [
    ('morning', _('Morning')),
    ('afternoon', _('Afternoon')),
    ('evening', _('Evening')),
    ('night', _('Night')),
]


class ConditionsForm(GuidedForm):
    availability = single(
        _('When could you start?'),
        [
            ('now', _('As soon as possible')),
            ('month', _('Within one month')),
            ('three_months', _('Within three months')),
            ('date', _('From a specific date')),
            DISCUSS,
        ],
        True,
    )
    available_from = forms.DateField(
        label=_('Available from'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    contract_types = multiple(
        _('Contracts I would accept'),
        [
            ('permanent', _('Permanent contract')),
            ('fixed', _('Fixed-term contract')),
            ('temporary', _('Temporary agency work')),
            ('seasonal', _('Seasonal work')),
            ('apprenticeship', _('Apprenticeship')),
            OTHER,
            DISCUSS,
        ],
        True,
    )
    contract_details = forms.CharField(
        label=_('Other contract: specify'), max_length=500, required=False
    )
    working_time = multiple(
        _('Working time I would accept'),
        [('full', _('Full-time')), ('part', _('Part-time')), DISCUSS],
        True,
    )
    schedule_preference = single(
        _('What are your schedule availabilities?'),
        [
            ('varied', _('I am available on varied schedules')),
            ('specific', _('I have schedule constraints or preferences')),
            DISCUSS,
        ],
        True,
    )
    schedule_strict = forms.BooleanField(
        label=_('These are my only available time slots'), required=False
    )
    condition_overrides = forms.JSONField(required=False, widget=forms.HiddenInput)
    auto_conditions = forms.JSONField(required=False, widget=forms.HiddenInput)
    working_conditions = multiple(
        _('Working hours and conditions I would accept'),
        [
            ('day', _('Daytime work')),
            (
                'early',
                pgettext_lazy('employer import-v2', 'Early starts or unusual hours'),
            ),
            ('night', pgettext_lazy('employer import-v2', 'Evening or night work')),
            (
                'weekend',
                _('Weekend work'),
            ),
            ('variable', pgettext_lazy('employer import-v2', 'Variable hours')),
            ('shift', pgettext_lazy('employer import-v2', 'Shift work')),
            ('split', pgettext_lazy('employer import-v2', 'Split shifts')),
            ('physical', pgettext_lazy('employer import-v2', 'Physical work')),
            ('standing', pgettext_lazy('employer import-v2', 'Prolonged standing')),
            ('outdoor', pgettext_lazy('employer import-v2', 'Outdoor work')),
            ('travel', pgettext_lazy('employer import-v2', 'Frequent travel')),
            ('none', _('None of these conditions')),
            DISCUSS,
        ],
        True,
    )
    condition_details = text_field(_('Additional details (optional)'))
    salary_preference = single(
        _('Salary expectations'),
        [
            ('discuss', _('To discuss')),
            ('minimum', _('I have a minimum amount in mind')),
        ],
        True,
    )
    salary_amount = forms.DecimalField(
        label=_('Minimum amount'),
        required=False,
        min_value=0,
        max_value=10000000,
        max_digits=11,
        decimal_places=2,
    )
    salary_currency = forms.ChoiceField(
        label=_('Currency'),
        required=False,
        choices=[
            ('', _('Choose an answer')),
            ('EUR', 'EUR'),
            ('CHF', 'CHF'),
            ('GBP', 'GBP'),
        ],
    )
    salary_period = forms.ChoiceField(
        label=_('Pay period'),
        required=False,
        choices=[
            ('', _('Choose an answer')),
            ('hour', _('Per hour')),
            ('month', _('Per month')),
            ('year', _('Per year')),
        ],
    )
    salary_basis = forms.ChoiceField(
        label=_('Gross or net'),
        required=False,
        choices=[('', _('Choose an answer')), ('gross', _('Gross')), ('net', _('Net'))],
    )
    exclusive = {
        'contract_types': ('discuss',),
        'working_time': ('discuss',),
        'working_conditions': ('none', 'discuss'),
    }
    other_details = {'contract_types': 'contract_details'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for day, label in SCHEDULE_DAYS:
            self.fields['schedule_' + day] = multiple(label, SCHEDULE_PERIODS)
        if (
            not self.is_bound
            and 'condition_overrides' not in self.initial
            and self.initial.get('working_conditions')
        ):
            self.initial['condition_overrides'] = list(DERIVED)
        if self.is_bound:
            if self.data.get('schedule_preference') != 'specific':
                self.fields['schedule_strict'].disabled = True
                self.initial['schedule_strict'] = False
                for day, label in SCHEDULE_DAYS:
                    name = 'schedule_' + day
                    self.fields[name].disabled = True
                    self.initial[name] = []
            if self.data.get('availability') != 'date':
                self.fields['available_from'].disabled = True
                self.initial['available_from'] = None
            if self.data.get('salary_preference') != 'minimum':
                for name in (
                    'salary_amount',
                    'salary_currency',
                    'salary_period',
                    'salary_basis',
                ):
                    self.fields[name].disabled = True
                    self.initial[name] = None

    def clean(self):
        data = super().clean()
        if data.get('schedule_preference') == 'specific' and not any(
            data.get('schedule_' + day) for day, label in SCHEDULE_DAYS
        ):
            self.add_error(
                'schedule_preference',
                _('Select at least one time slot, or choose the discussion option.'),
            )
        for name in ('condition_overrides', 'auto_conditions'):
            values = data.get(name) or []
            if (
                not isinstance(values, list)
                or len(values) > 3
                or any(
                    not isinstance(value, str) or value not in DERIVED
                    for value in values
                )
            ):
                self.add_error(
                    name,
                    _('Invalid schedule suggestion state. Please reload the page.'),
                )
            else:
                data[name] = list(dict.fromkeys(values))
        conflict_labels = {
            'day': _('Daytime work'),
            'night': pgettext_lazy('employer import-v2', 'Evening or night work'),
            'weekend': _('Weekend work'),
        }
        conflicts = inconsistent_conditions(data)
        if conflicts:
            self.add_error(
                'working_conditions',
                _(
                    'Your exclusive schedule has no matching slot for: %(conditions)s. Change the grid or these choices.'
                )
                % {
                    'conditions': ', '.join(
                        str(conflict_labels[value]) for value in conflicts
                    )
                },
            )
        if data.get('availability') == 'date' and not data.get('available_from'):
            self.add_error('available_from', _('Choose a date.'))
        if data.get('availability') != 'date':
            data['available_from'] = None
        if data.get('salary_preference') == 'minimum':
            for name in (
                'salary_amount',
                'salary_currency',
                'salary_period',
                'salary_basis',
            ):
                if data.get(name) in (None, ''):
                    self.add_error(
                        name,
                        _('Complete the amount, currency, period and gross/net basis.'),
                    )
        else:
            for name in (
                'salary_amount',
                'salary_currency',
                'salary_period',
                'salary_basis',
            ):
                data[name] = ''
        return data


class ContactForm(forms.Form):
    display_name = forms.CharField(
        label=_('Name to display'),
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'name'}),
    )
    contact_email = forms.EmailField(
        label=_('Email for confirmation'),
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    reviewed = forms.BooleanField(
        label=_('I have reviewed my answers and read the data protection notice.')
    )

    def clean_contact_email(self):
        return self.cleaned_data['contact_email'].strip().lower()


FORMS = {1: ProjectForm, 2: MobilityForm, 3: ConditionsForm, 4: ContactForm}
TITLES = {
    1: _('My project'),
    2: _('Mobility and languages'),
    3: _('My conditions'),
    4: _('Review my project'),
}
SCHEMA = 2


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
    from . import registration

    def go(step):
        return redirect(f'/candidate/prepare/?step={step}&lang={language}')

    draft = request.session.get(KEY)
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
            ('search', 'continue')
            if step == 1
            else ('finish',) if step == 4 else ('continue',)
        )
        if action not in allowed_actions:
            return HttpResponseBadRequest()
    form_class = FORMS[step]
    initial = draft['data']
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
        **({'language': language} if step == 1 else {}),
    )
    if step == 4 and draft.get('editing_user'):
        form.fields['contact_email'].disabled = True
    if request.method == 'POST' and action != 'search' and form.is_valid():
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
                registration.update_profile(request.user, draft['data'], language)
                destination = 'candidate_profile'
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
            request.session.pop(KEY, None)
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
            for name, field in FORMS[number]().fields.items():
                value = draft['data'].get(name, '')
                if name in (
                    'occupation_query',
                    'condition_overrides',
                    'auto_conditions',
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
            if name == 'occupation_references':
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
