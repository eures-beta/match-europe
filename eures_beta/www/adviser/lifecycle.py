"""Matching-centred work list, life line and explicit outcomes."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.matching import (
    access,
    match_lifecycle as service,
    introduction_followup,
)
from eures_beta.matching.models import CandidateOfferConversation
from eures_beta.users.email_login import email_ready
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.forms import bootstrap_form
from .followup import ReminderForm
from .matching import render_workspace, pending_pairs


class CheckInForm(forms.Form):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    due_on = forms.DateField(
        label=_('When will you check this matching again?'),
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )


class OutcomeForm(forms.Form):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    start_on = forms.DateField(
        label=_('Expected start date, if known'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    verified = forms.BooleanField(
        label=_('I have checked this hiring with the employer or candidate.'),
        required=False,
    )
    reason = forms.CharField(
        label=_('Reason for stopping this matching'),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={'rows': 3}),
    )


def row(match, user):
    item = service.summary(match)
    review = item['review']
    action = item['action']
    url = reverse('adviser_match_lifecycle', args=[match.pk])
    labels = dict(
        examine=_('Examine this matching'),
        propose=_('Prepare the offer proposal'),
        review=_('Review the replies'),
        prepare_employer=_('Prepare the employer request'),
        candidate_reminder=_('Prepare a reminder for the candidate'),
        employer_reminder=_('Prepare a reminder for the employer'),
        open=_('Open the three-way conversation'),
        conversation=_('Open the conversation'),
        confirm=_('Confirm the hiring and close'),
        none=_('View the matching history'),
    )
    anchor = ''
    if action == 'examine':
        url = reverse(
            (
                'adviser_match'
                if pending_pairs().filter(pk=match.pk).exists()
                else 'matching_detail'
            ),
            args=[match.pk],
        )
    elif action == 'propose':
        url = reverse('matching_detail', args=[match.pk])
    elif action == 'review':
        url = reverse('adviser_conversation', args=[review.pk]) if review else url
    elif action in ('prepare_employer', 'open'):
        if review.assigned_to_adviser_id == user.pk:
            url = reverse(
                (
                    'prepare_employer_consent'
                    if action == 'prepare_employer'
                    else 'shared_conversation_start'
                ),
                args=[review.pk],
            )
        else:
            url, labels[action] = reverse('adviser_conversation', args=[review.pk]), _(
                'Take over this review'
            )
    elif action in ('candidate_reminder', 'employer_reminder'):
        anchor = '#reminder'
    elif action == 'confirm':
        anchor = '#conclusion'
    elif action == 'conversation':
        if item['thread'].adviser_id == user.pk:
            url = reverse('shared_conversation', args=[item['thread'].pk])
        else:
            url, labels[action] = reverse('adviser_conversation', args=[review.pk]), _(
                'Take over this review'
            )
    item.update(
        action_label=labels[action],
        action_url=url,
        action_anchor=anchor,
        waiting_label=dict(
            adviser=_('Adviser'), candidate=_('Candidate'), employer=_('Employer')
        )[item['waiting']],
        waiting_days=max(
            0, (timezone.localdate() - timezone.localdate(item['stage_since'])).days
        ),
    )
    if item['plan'] and item['plan'].due_on:
        days = (item['plan'].due_on - timezone.localdate()).days
        if days < 0:
            item['date_status'] = ngettext(
                'Check-in overdue by %(days)s day',
                'Check-in overdue by %(days)s days',
                -days,
            ) % {'days': -days}
        elif days == 0:
            item['date_status'] = _('Check in today')
        else:
            item['date_status'] = ngettext(
                'Next check-in in %(days)s day', 'Next check-in in %(days)s days', days
            ) % {'days': days}
    return item


CLOSED = (
    Q(decision='refused')
    | Q(candidate_offer_review__workflow_state='refused')
    | Q(followup__outcome='stopped')
    | Q(conclusion__state__in=['hired', 'stopped'])
)


@never_cache
@login_required(login_url='magic_login')
@require_http_methods(['GET', 'HEAD'])
def index(request):
    access.guard(request)
    with translation.override(selected_language(request)):
        query = service.matches()
        active = query.exclude(CLOSED)
        closed = request.GET.get('closed') == '1'
        due_only = not closed and request.GET.get('due') == '1'
        section = request.GET.get('filter', 'all')
        counts = active.aggregate(
            total=Count('pk'),
            due=Count('pk', filter=Q(followup__due_on__lte=timezone.localdate())),
            unplanned=Count('pk', filter=Q(followup__due_on__isnull=True)),
            upcoming=Count('pk', filter=Q(followup__due_on__gt=timezone.localdate())),
            confirm=Count('pk', filter=Q(conclusion__state='reported')),
            examine=Count('pk', filter=Q(decision='pending')),
        )
        query = query.filter(CLOSED) if closed else active
        if due_only:
            query = query.filter(followup__due_on__lte=timezone.localdate())
        elif section == 'unplanned':
            query = query.filter(followup__due_on__isnull=True)
        elif section == 'upcoming':
            query = query.filter(followup__due_on__gt=timezone.localdate())
        elif section == 'confirm':
            query = query.filter(conclusion__state='reported')
        elif section == 'examine':
            query = query.filter(decision='pending')
        query = query.annotate(
            priority=Case(
                When(conclusion__state='reported', then=Value(0)),
                When(followup__due_on__lte=timezone.localdate(), then=Value(1)),
                When(decision='pending', then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('priority', F('followup__due_on').asc(nulls_last=True), 'pk')
        page = Paginator(query, 20).get_page(request.GET.get('page'))
        return render_workspace(
            request,
            'adviser_matching_lifecycle_list.html',
            rows=[row(match, request.user) for match in page],
            page=page,
            counts=counts,
            closed=closed,
            due_only=due_only,
            followup_section=section,
            followup_tab=True,
        )


@never_cache
@login_required(login_url='magic_login')
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    access.guard(request)
    language = selected_language(request)
    with translation.override(language):
        match = get_object_or_404(service.matches(), pk=pk)
        item = row(match, request.user)
        review, plan = item['review'], item['plan']
        current = introduction_followup.context(review) if review else None
        recipients = current['recipients'] if current else {}
        role = (
            item['waiting']
            if item['waiting'] in recipients
            else next(iter(recipients), 'candidate')
        )
        action = request.POST.get('action', '') if request.method == 'POST' else ''
        schedule = CheckInForm(
            request.POST if action == 'schedule' else None,
            initial={
                'version': plan.version if plan else 0,
                'due_on': plan.due_on if plan else None,
            },
            auto_id='schedule_%s',
        )
        outcome = OutcomeForm(
            request.POST if action in ('hired', 'stopped') else None,
            initial={
                'version': item['version'],
                'start_on': item['conclusion'].start_on if item['conclusion'] else None,
            },
            auto_id='outcome_%s',
        )
        reminder = ReminderForm(
            recipients,
            request.POST if action == 'reminder' else None,
            initial={
                'stamp': current['stamp'] if current else '',
                'recipient': role,
                'language': language,
                'message': introduction_followup.draft(role),
            },
            auto_id='reminder_%s',
        )
        error, status = '', 200
        if request.method == 'POST':
            form = (
                schedule
                if action == 'schedule'
                else reminder if action == 'reminder' else outcome
            )
            if (
                action not in ('schedule', 'reminder', 'hired', 'stopped')
                or not form.is_valid()
            ):
                status = 400
            else:
                try:
                    if action == 'schedule':
                        service.schedule(
                            request.user,
                            pk,
                            waiting_for=item['waiting'],
                            next_action=str(item['stage']),
                            **form.cleaned_data,
                        )
                    elif action == 'reminder':
                        if not review:
                            raise Http404
                        introduction_followup.reminder(
                            request.user, review.pk, **form.cleaned_data
                        )
                    else:
                        service.conclude(request.user, pk, action, **form.cleaned_data)
                    return redirect(
                        reverse('adviser_match_lifecycle', args=[pk])
                        + '?lang='
                        + language
                        + '&saved='
                        + action
                        + '#matching-title'
                    )
                except (service.Changed, introduction_followup.Changed):
                    error, status = (
                        _('This matching changed. Reload it before acting.'),
                        409,
                    )
                except introduction_followup.RetryLater:
                    error, status = _('Wait a moment before resending.'), 429
                except ValidationError as exc:
                    error, status = exc.messages[0], 400
        events = []
        for decision in match.decisions.select_related('by_adviser').order_by('pk'):
            events.append(
                dict(
                    date=decision.created_at,
                    label=(
                        _('Matching retained')
                        if decision.value == 'retained'
                        else _('Matching declined')
                    ),
                    actor=decision.by_adviser,
                )
            )
        if review:
            events += [
                dict(date=e.created_at, label=e.get_action_display(), actor=e.actor)
                for e in review.events.select_related('actor')
            ]
        if plan:
            for event in plan.events.select_related('actor'):
                label = event.get_action_display()
                detail = event.snapshot.get('next_action', '')
                if event.action == 'reminder':
                    label = (
                        str(label)
                        + ' · '
                        + str(event.get_recipient_display())
                        + ' · '
                        + str(event.get_delivery_status_display())
                    )
                    detail = event.message
                events.append(
                    dict(
                        date=event.created_at,
                        label=label,
                        actor=event.actor,
                        detail=detail,
                    )
                )
        if item['conclusion']:
            events += [
                dict(date=e.created_at, label=e.get_action_display(), actor=e.actor)
                for e in item['conclusion'].events.select_related('actor')
            ]
        reminder_result = (
            plan.events.filter(action='reminder').order_by('-pk').first()
            if plan and request.GET.get('saved') == 'reminder'
            else None
        )
        return render_workspace(
            request,
            'adviser_matching_lifecycle_detail.html',
            status=status,
            dossier=item,
            schedule_form=bootstrap_form(schedule),
            outcome_form=bootstrap_form(outcome),
            reminder_form=bootstrap_form(reminder),
            recipients=recipients,
            events=sorted(events, key=lambda e: e['date'], reverse=True),
            error=error,
            saved=request.GET.get('saved'),
            reminder_result=reminder_result,
            email_available=email_ready(),
            followup_tab=True,
        )


@never_cache
@login_required(login_url='magic_login')
@require_http_methods(['GET', 'POST'])
def report_hiring(request, pk):
    language = selected_language(request)
    with translation.override(language):
        match = get_object_or_404(service.matches(), pk=pk)
        if not service.can_report(request.user, match):
            raise Http404
        form = OutcomeForm(
            request.POST if request.method == 'POST' else None, initial={'version': 0}
        )
        del form.fields['verified']
        del form.fields['reason']
        error, status = '', 200
        if request.method == 'POST' and form.is_valid():
            try:
                service.conclude(request.user, pk, 'reported', **form.cleaned_data)
                thread = CandidateOfferConversation.objects.get(
                    offer_review__match=match
                )
                return redirect(
                    reverse('shared_conversation', args=[thread.pk])
                    + '?lang='
                    + language
                )
            except service.Changed:
                error, status = (
                    _('This matching changed. Reload it before acting.'),
                    409,
                )
        return render(
            request,
            'matching/report_hiring.html',
            {
                'matching': match,
                'form': bootstrap_form(form),
                'error': error,
                'page_language': language,
            },
            status=400 if form.errors else status,
        )
