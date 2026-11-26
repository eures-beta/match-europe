"""Adviser-only planning and explicit, previewed reminders."""

from django import forms
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.matching import access, introduction_followup as service
from eures_beta.matching.models import IntroductionFollowup
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.design_system import bootstrap_form
from .matching import render_workspace


class PlanForm(forms.Form):
    stamp = forms.CharField(widget=forms.HiddenInput, max_length=64)
    next_action = forms.CharField(label=_('Next action'), max_length=500)
    waiting_for = forms.ChoiceField(
        label=_('Action expected from'), choices=IntroductionFollowup.WaitingFor.choices
    )
    due_on = forms.DateField(
        label=_('Follow-up date'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    outcome = forms.ChoiceField(
        label=_('Outcome'), choices=IntroductionFollowup.Outcome.choices
    )
    closure_reason = forms.CharField(
        label=_('Reason for closing'),
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def clean(self):
        data = super().clean()
        if data.get('outcome') == 'open' and not data.get('due_on'):
            self.add_error('due_on', _('Choose when to check this dossier again.'))
        if data.get('outcome') in ('hired', 'stopped') and not data.get(
            'closure_reason'
        ):
            self.add_error(
                'closure_reason', _('Give a reason for closing this follow-up.')
            )
        return data


class ReminderForm(forms.Form):
    stamp = forms.CharField(widget=forms.HiddenInput, max_length=64)
    recipient = forms.ChoiceField(label=_('Recipient'))
    language = forms.ChoiceField(
        label=_('Email language'),
        choices=[('fr', 'Français'), ('en', 'English'), ('de', 'Deutsch')],
    )
    message = forms.CharField(
        label=_('Reminder message'),
        max_length=2000,
        widget=forms.Textarea(attrs={'rows': 5}),
    )

    def __init__(self, recipients, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].choices = [
            (role, dict(IntroductionFollowup.WaitingFor.choices)[role])
            for role in recipients
        ]


@never_cache
@require_http_methods(['GET'])
def index(request):
    access.guard(request)
    with translation.override(selected_language(request)):
        closed = request.GET.get('closed') == '1'
        due_only = not closed and request.GET.get('due') == '1'
        query = service.reviews()
        if closed:
            query = query.filter(
                introduction_followup__outcome__in=['hired', 'stopped']
            )
        else:
            query = query.exclude(
                introduction_followup__outcome__in=['hired', 'stopped']
            )
        if due_only:
            query = query.filter(
                introduction_followup__due_on__lte=timezone.localdate()
            )
        query = query.order_by(
            F('introduction_followup__due_on').asc(nulls_first=True), 'pk'
        )
        page = Paginator(query, 20).get_page(request.GET.get('page'))
        rows = [dict(review=review, **service.context(review)) for review in page]
        return render_workspace(
            request,
            'adviser_followup_list.html',
            page=page,
            rows=rows,
            closed=closed,
            due_only=due_only,
            followup_tab=True,
        )


@never_cache
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    access.guard(request)
    language = selected_language(request)
    with translation.override(language):
        review = get_object_or_404(service.reviews(), pk=pk)
        current = service.context(review)
        plan = current['plan']
        action = request.POST.get('action') if request.method == 'POST' else ''
        initial = (
            {
                key: getattr(plan, key)
                for key in (
                    'next_action',
                    'waiting_for',
                    'due_on',
                    'outcome',
                    'closure_reason',
                )
            }
            if plan
            else {'waiting_for': current['waiting'], 'outcome': 'open'}
        )
        initial['stamp'] = current['stamp']
        plan_form = PlanForm(
            request.POST if action == 'plan' else None,
            initial=initial,
            auto_id='plan_%s',
        )
        role = request.GET.get(
            'recipient', plan.waiting_for if plan else current['waiting']
        )
        if role not in current['recipients']:
            role = next(iter(current['recipients']), 'candidate')
        reminder_form = ReminderForm(
            current['recipients'],
            request.POST if action == 'reminder' else None,
            auto_id='reminder_%s',
            initial={
                'stamp': current['stamp'],
                'recipient': role,
                'message': service.draft(role),
                'language': language,
            },
        )
        error, status = '', 200
        if request.method == 'POST':
            form = plan_form if action == 'plan' else reminder_form
            if action not in ('plan', 'reminder') or not form.is_valid():
                status = 400
            else:
                try:
                    if action == 'plan':
                        service.plan(request.user, pk, **form.cleaned_data)
                    else:
                        service.reminder(request.user, pk, **form.cleaned_data)
                    return redirect(
                        reverse('adviser_followup', args=[pk])
                        + '?lang='
                        + language
                        + '&saved=1'
                    )
                except service.Changed:
                    error, status = (
                        _('This dossier changed. Reload it before acting.'),
                        409,
                    )
                except service.RetryLater:
                    error, status = _('Wait a moment before resending.'), 429
                except ValidationError as exc:
                    error, status = exc.messages[0], 400
        return render_workspace(
            request,
            'adviser_followup_detail.html',
            status=status,
            review=review,
            followup=current,
            plan_form=bootstrap_form(plan_form),
            reminder_form=bootstrap_form(reminder_form),
            events=plan.events.select_related('actor').order_by('-pk') if plan else [],
            followup_tab=True,
            error=error,
            saved=request.GET.get('saved') == '1',
        )
