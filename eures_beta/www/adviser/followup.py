"""Adviser-only planning and explicit, previewed reminders."""

from django import forms
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.matching import access, introduction_followup as service
from eures_beta.matching.models import IntroductionFollowup
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.forms import bootstrap_form
from eures_beta.users.email_login import email_ready
from .matching import render_workspace


class PlanForm(forms.Form):
    stamp = forms.CharField(widget=forms.HiddenInput, max_length=64)
    next_action = forms.CharField(label=_('What needs to happen next?'), max_length=500)
    waiting_for = forms.ChoiceField(
        label=_('Who needs to act?'), choices=IntroductionFollowup.WaitingFor.choices
    )
    due_on = forms.DateField(
        label=_('When will you check this dossier again?'),
        help_text=_(
            'Choose your next check-in date. No reminder is sent automatically.'
        ),
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


def presentation(review, current):
    """Concrete dates and actions, without inventing a response deadline."""
    today = timezone.localdate()
    plan = current['plan']
    role = plan.waiting_for if plan else current['waiting']
    role_label = dict(IntroductionFollowup.WaitingFor.choices)[role]
    default_action = {
        'candidate': _('Collect the candidate’s reply'),
        'employer': _('Collect the employer’s decision'),
        'adviser': _('Review the replies and decide on the next step'),
    }[current['waiting']]
    status = _('No check-in date set')
    tone = 'info'
    delta = None
    if plan and plan.outcome != 'open':
        status = plan.get_outcome_display()
    elif plan and plan.due_on:
        delta = (plan.due_on - today).days
        if delta < 0:
            status = ngettext(
                'Check-in overdue by %(days)s day',
                'Check-in overdue by %(days)s days',
                -delta,
            ) % {'days': -delta}
            tone = 'danger'
        elif delta == 0:
            status, tone = _('Check in today'), 'warning'
        else:
            status = ngettext(
                'Next check-in in %(days)s day', 'Next check-in in %(days)s days', delta
            ) % {'days': delta}
    tracked_days = (
        (today - timezone.localdate(current['waiting_since'])).days
        if current['waiting_since']
        else None
    )
    opened_days = (today - timezone.localdate(review.created_at)).days
    detail_url = reverse('adviser_followup', args=[review.pk])
    action_url, action_label, anchor = (
        detail_url,
        _('Set the next check-in date'),
        '#planning',
    )
    if plan and current['recipients'] and role != 'adviser':
        target = (
            role if role in current['recipients'] else next(iter(current['recipients']))
        )
        action_label = (
            _('Prepare a reminder for the candidate')
            if target == 'candidate'
            else _('Prepare a reminder for the employer')
        )
        anchor = '#reminder'
    elif (current['waiting'] == 'adviser' or role == 'adviser') and (
        not plan or plan.outcome == 'open'
    ):
        action_url, action_label, anchor = (
            reverse('adviser_conversation', args=[review.pk]),
            _('Examine this dossier'),
            '',
        )
    if plan and plan.outcome != 'open':
        action_label, anchor = _('View the closed follow-up'), '#overview'
    return dict(
        **current,
        status_label=status,
        status_tone=tone,
        waiting_label=role_label,
        proposed_action=default_action,
        action_label=action_label,
        action_url=action_url,
        action_anchor=anchor,
        tracked_days=tracked_days,
        opened_days=opened_days,
    )


@never_cache
@require_http_methods(['GET'])
def index(request):
    access.guard(request)
    with translation.override(selected_language(request)):
        closed = request.GET.get('closed') == '1'
        due_only = not closed and request.GET.get('due') == '1'
        section = request.GET.get('filter', 'all')
        if section not in ('all', 'unplanned', 'upcoming'):
            section = 'all'
        query = service.reviews()
        active = query.exclude(introduction_followup__outcome__in=['hired', 'stopped'])
        counts = active.aggregate(
            total=Count('pk'),
            due=Count(
                'pk', filter=Q(introduction_followup__due_on__lte=timezone.localdate())
            ),
            unplanned=Count('pk', filter=Q(introduction_followup__due_on__isnull=True)),
            upcoming=Count(
                'pk', filter=Q(introduction_followup__due_on__gt=timezone.localdate())
            ),
        )
        if (
            not closed
            and 'filter' not in request.GET
            and 'due' not in request.GET
            and counts['due']
        ):
            due_only = True
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
        elif not closed and section == 'unplanned':
            query = query.filter(introduction_followup__due_on__isnull=True)
        elif not closed and section == 'upcoming':
            query = query.filter(introduction_followup__due_on__gt=timezone.localdate())
        query = query.order_by(
            F('introduction_followup__due_on').asc(nulls_last=True), 'pk'
        )
        page = Paginator(query, 20).get_page(request.GET.get('page'))
        rows = [
            dict(review=review, **presentation(review, service.context(review)))
            for review in page
        ]
        return render_workspace(
            request,
            'adviser_followup_list.html',
            page=page,
            rows=rows,
            closed=closed,
            due_only=due_only,
            followup_section=section,
            counts=counts,
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
        current = presentation(review, service.context(review))
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
            else {
                'waiting_for': current['waiting'],
                'outcome': 'open',
                'next_action': current['proposed_action'],
            }
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
                        + '&saved='
                        + action
                        + '#overview'
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
            saved=request.GET.get('saved', ''),
            reminder_result=(
                plan.events.filter(action='reminder').order_by('-pk').first()
                if plan and request.GET.get('saved') == 'reminder'
                else None
            ),
            email_available=email_ready(),
        )
