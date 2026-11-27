"""Adviser review of Django matchings and follow-up of candidate conversations."""

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils import timezone
from django.utils.translation import get_language_info, gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from types import SimpleNamespace

from eures_beta.candidates.occupation_choices import resolve_reference
from eures_beta.matching import (
    access,
    adviser_opinion,
    dialogue_albert,
    employer_consent,
    offer_review_services,
    dialogue_services,
    services,
    review_email,
    review_workflow,
)
from eures_beta.www.matching.offer_reviews import display_rows
from eures_beta.matching.models import (
    CandidateOfferReview,
    MatchEvaluation,
    CandidateOfferMatch,
    MatchFollowup,
    MatchConclusion,
)
from eures_beta.matching.presentation import present
from eures_beta.www.matching.conversations import listed
from eures_beta.www.accounts.views import selected_language


def language_label(code):
    try:
        return get_language_info(code)['name_translated']
    except KeyError:
        return code


class ReviewForm(forms.Form):
    evaluation = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    action = forms.ChoiceField(
        choices=[(key, key) for key in ('retained', 'refused', 'refresh')]
    )


class HandlingForm(forms.Form):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    fingerprint = forms.CharField(max_length=64, widget=forms.HiddenInput)
    public_message = forms.CharField(
        label=_('Message to the candidate'),
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    internal_note = forms.CharField(
        label=_('Internal note — advisers only'),
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    action = forms.ChoiceField(
        choices=[
            (key, key)
            for key in (
                'claim',
                'release',
                'takeover',
                'validated',
                'clarify',
                'refused',
            )
        ],
        widget=forms.HiddenInput,
    )


def eligible_pairs():
    return CandidateOfferMatch.objects.filter(
        candidate__in=access.candidates(), offer__in=access.matchable_offers()
    ).select_related('candidate__user', 'offer')


def pending_pairs():
    latest = MatchEvaluation.objects.filter(match_id=OuterRef('pk')).order_by('-pk')
    return (
        eligible_pairs()
        .filter(decision='pending')
        .annotate(
            evaluation_id=Subquery(latest.values('pk')[:1]),
            score=Subquery(latest.values('result__established')[:1]),
            result_status=Subquery(latest.values('result__status')[:1]),
        )
        .filter(result_status='review')
    )


def open_conversations():
    return CandidateOfferReview.objects.filter(
        match__in=eligible_pairs().filter(decision='retained')
    ).select_related('match__candidate__user', 'match__offer', 'assigned_to_adviser')


def render_workspace(request, template, status=200, **context):
    if access.can_view_pairs(request.user):
        context['followup_due_count'] = MatchFollowup.objects.filter(
            outcome='open', due_on__lte=timezone.localdate()
        ).count()
        context['hiring_confirmation_count'] = MatchConclusion.objects.filter(
            state='reported'
        ).count()
        context['ready_review_count'] = (
            open_conversations().filter(workflow_state='ready').count()
        )
        context['initiated_review_count'] = (
            open_conversations()
            .filter(workflow_state='ready', requested_by_adviser=request.user)
            .count()
        )
    return render(
        request,
        'users/' + template,
        dict(context, matching_tab=True, dashboard_language=selected_language(request)),
        status=status,
    )


def queue(request):
    from .action_queue import queue_page

    return queue_page(request)


@transaction.atomic
def record_review(user, match, evaluation_id, action):
    match = CandidateOfferMatch.objects.select_for_update().get(pk=match.pk)
    if match.decision != 'pending':
        raise services.StaleEvaluation
    if action == 'refresh':
        services.calculate(match.candidate, match.offer)
        return
    if action == 'retained' and not dialogue_services.enabled():
        raise ValidationError(_('Albert is currently unavailable. Try again later.'))
    services.decide(match.pk, evaluation_id, action, by_adviser=user)
    if action == 'retained':
        confirmation, _created = CandidateOfferReview.objects.get_or_create(
            match=match, defaults={'requested_by_adviser': user}
        )
        transaction.on_commit(lambda: review_email.send(confirmation.pk))


@never_cache
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    access.guard(request)
    language = selected_language(request)
    with translation.override(language):
        match = get_object_or_404(pending_pairs(), pk=pk)
        evaluation = get_object_or_404(MatchEvaluation, pk=match.evaluation_id)
        status, error = 200, ''
        if request.method == 'POST':
            form = ReviewForm(request.POST)
            try:
                if not form.is_valid():
                    raise ValidationError(_('Select a valid matching decision.'))
                action = form.cleaned_data['action']
                record_review(
                    request.user, match, form.cleaned_data['evaluation'], action
                )
                if action == 'refresh' and pending_pairs().filter(pk=pk).exists():
                    return redirect(
                        reverse('adviser_match', args=[pk]) + '?lang=' + language
                    )
                view = '&view=conversations' if action == 'retained' else ''
                return redirect(reverse('dashboard') + '?lang=' + language + view)
            except (services.StaleEvaluation, ObjectDoesNotExist, ValueError):
                status = 409
                error = _(
                    'This matching has changed. Refresh the evaluation before deciding.'
                )
            except ValidationError as exc:
                status, error = 400, exc.messages[0]
        return render_workspace(
            request,
            'adviser_match_detail.html',
            status,
            matching=matching_context(request, match, evaluation),
            error=error,
        )


def group_criteria(rows):
    groups = {}
    for row in rows:
        references = groups.setdefault(str(row['label']), {})
        if row['reference_label']:
            references[str(row['reference_label'])] = None
    return [(label, list(references)) for label, references in groups.items()]


def comparison_rows(rows):
    for row in rows:
        expected = row['expected_label']
        declared = row['declared_label']
        reference = row['reference_label']
        if row['key'] in ('skill', 'permit', 'work_condition', 'contract', 'mobility'):
            expected = expected or reference
            if row['state'] == 'match':
                declared = declared or reference
        if expected or declared:
            yield dict(row, expected_label=expected, declared_label=declared)


def matching_context(request, match, evaluation):
    language = selected_language(request)
    try:
        stale = evaluation.fingerprint != services.inputs(match)[1]
    except (ObjectDoesNotExist, ValidationError, ValueError):
        stale = True
    result = present(evaluation.result, language)
    if stale:
        rating = ('amber', _('Score to update'))
    elif result['blocked'] or result['established'] + result['unresolved'] < 50:
        rating = ('red', _('Not recommended'))
    elif result['established'] >= 70 and not result['incompatibilities']:
        rating = ('green', _('Recommended'))
    else:
        rating = ('amber', _('Borderline'))
    return dict(
        match=match,
        evaluation=evaluation,
        rating=rating,
        dimensions=result['dimensions'],
        comparisons=list(comparison_rows(result['rows'])),
        criteria=[
            (_('Incompatibilities'), group_criteria(result['incompatibilities']), ''),
            (
                _('Information to clarify'),
                group_criteria(result['unknowns']),
                _(
                    'The information available about the offer or the candidate is insufficient to assess these points.'
                ),
            ),
            (_('Compatible points'), group_criteria(result['strengths']), ''),
        ],
        occupations=[
            occupation['label']
            for reference in match.candidate.occupation_references
            if (occupation := resolve_reference(reference, language))
        ],
        languages=[
            (language_label(row['code']), row['level'])
            for row in match.candidate.language_skills.get('languages', [])
        ],
        stale=stale,
        can_decide=access.can_change_match(request.user),
        albert_available=dialogue_services.enabled(),
    )


@never_cache
@require_http_methods(['GET', 'POST'])
def follow(request, pk):
    access.guard(request)
    with translation.override(selected_language(request)):
        conversation = get_object_or_404(open_conversations(), pk=pk)
        can_resend = (
            access.can_change_match(request.user)
            and conversation.workflow_state != 'refused'
            and not hasattr(conversation.match, 'conclusion')
        )
        language = selected_language(request)
        state = offer_review_services.review_state(conversation)
        rows = display_rows(state['rows'], language)
        answer_labels = {
            'yes': _('Yes'),
            'conditional': _('Under conditions'),
            'no': _('No'),
            'changed': _('My situation changed'),
            'clarify': _('More details needed'),
        }
        for row in rows:
            row['followup_answer'] = (
                answer_labels[row['answer'].value] if row['answer'] else ''
            )
        total = sum(row['askable'] for row in rows)
        answered = sum(
            row['askable'] and not offer_review_services.needs_answer(row)
            for row in rows
        )
        progress = (
            _('Offer declined')
            if state['declined']
            else (
                _('Replies complete')
                if total and answered == total
                else (_('In progress') if answered else _('Not started'))
            )
        )
        ready = adviser_opinion.ready(state)
        can_analyse = ready and dialogue_services.enabled()
        key = adviser_opinion.cache_key(pk, state['fingerprint'], language)
        opinion = cache.get(key) if can_analyse else None
        result, error, status = '', '', 200
        action = request.POST.get('action')
        handling = HandlingForm(
            (
                request.POST
                if action
                in {'claim', 'release', 'takeover', 'validated', 'clarify', 'refused'}
                else None
            ),
            initial={
                'version': conversation.workflow_version,
                'fingerprint': state['fingerprint'],
            },
        )
        if request.method == 'POST' and action in {
            'claim',
            'release',
            'takeover',
            'validated',
            'clarify',
            'refused',
        }:
            try:
                if not handling.is_valid():
                    raise ValidationError('Invalid handling form')
                review_workflow.handle(request.user, pk, **handling.cleaned_data)
                return redirect(
                    reverse('adviser_conversation', args=[pk]) + '?lang=' + language
                )
            except (services.StaleEvaluation, ObjectDoesNotExist):
                error, status = _('This review changed. Reload it before acting.'), 409
            except ValidationError:
                error, status = (
                    _(
                        'Enter a message for the candidate; a takeover also needs an internal reason.'
                    ),
                    400,
                )
        elif request.method == 'POST' and action == 'analyse':
            if (
                not can_analyse
                or request.POST.get('fingerprint') != state['fingerprint']
            ):
                error, status = (
                    _('The conversation changed or analysis is unavailable.'),
                    409,
                )
            elif opinion is None:
                try:
                    opinion = adviser_opinion.generate(request.user, rows, language)
                except dialogue_albert.Unavailable:
                    error, status = (
                        _('Albert could not analyse the replies. Try again later.'),
                        503,
                    )
                else:
                    current = open_conversations().filter(pk=pk).first()
                    if (
                        current is None
                        or offer_review_services.review_state(current)['fingerprint']
                        != state['fingerprint']
                    ):
                        return redirect(
                            reverse('adviser_conversation', args=[pk])
                            + '?lang='
                            + language
                        )
                    cache.set(key, opinion, 3600)
        elif request.method == 'POST':
            if not can_resend or action != 'resend':
                raise Http404
            try:
                sent = review_email.send(pk, adviser=request.user)
                conversation.refresh_from_db()
                result = conversation.get_email_status_display()
                if not sent:
                    status = 503
            except review_email.RetryLater:
                result, status = _('Wait a moment before resending.'), 429
        events = list(conversation.events.select_related('actor').order_by('-version'))
        for event in events:
            event.saved_rows = display_rows(
                [
                    {
                        **row,
                        'askable': row['presented']['askable'],
                        'answer': (
                            SimpleNamespace(value=row['value'], detail=row['detail'])
                            if row['value']
                            else None
                        ),
                    }
                    for row in event.snapshot.get('answers', [])
                ],
                language,
            )
        return render_workspace(
            request,
            'adviser_conversation.html',
            status=status,
            can_resend=can_resend,
            resend_result=result,
            conversation=conversation,
            tracking=True,
            match=conversation.match,
            rows=rows,
            reply_total=total,
            reply_count=answered,
            reply_progress=progress,
            analysis_ready=ready,
            can_prepare_employer=(
                employer_consent.can_prepare(conversation, state, request.user)
                and bool(conversation.match.offer.employer_id)
            ),
            can_start_shared=bool(
                employer_consent.introduction_consent(conversation, state, request.user)
            ),
            can_analyse=can_analyse and access.can_change_match(request.user),
            analysis_fingerprint=state['fingerprint'],
            analysis_error=error,
            opinion=opinion,
            handling_form=handling,
            handling_current=review_workflow.current(conversation, state),
            handling_owned=conversation.assigned_to_adviser_id == request.user.pk,
            handling_events=events,
            recommendation=(
                adviser_opinion.LABELS[opinion['recommendation']] if opinion else ''
            ),
            simulated_opinion=settings.ALBERT_SIMULATED,
        )
