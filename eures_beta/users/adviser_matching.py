"""Adviser review of Django matchings and follow-up of candidate conversations."""

from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import get_language_info, gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from eures_beta.candidates import preview_push
from eures_beta.candidates.models import PreviewPushSubscription
from eures_beta.candidates.occupation_choices import resolve_reference
from eures_beta.matching import (
    access,
    confirmation_services,
    dialogue_services,
    services,
)
from eures_beta.matching.confirmation_views import display_rows
from eures_beta.matching.models import (
    CandidateOfferReview,
    MatchEvaluation,
    CandidateOfferMatch,
)
from eures_beta.matching.presentation import present
from .test_accounts import PWA_ACCOUNTS
from .views import selected_language


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


def eligible_pairs():
    return CandidateOfferMatch.objects.filter(
        candidate__in=access.candidates(), offer__in=access.matchable_offers()
    ).select_related('candidate__user', 'offer')


def pending_pairs():
    latest = MatchEvaluation.objects.filter(pair_id=OuterRef('pk')).order_by('-pk')
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
    return (
        CandidateOfferReview.objects.filter(
            pair__in=eligible_pairs().filter(decision='retained')
        )
        .filter(
            ~Exists(
                CandidateOfferReview.objects.filter(
                    pk=OuterRef('pk'), agreements__isnull=False
                )
            )
        )
        .select_related('pair__candidate__user', 'pair__offer')
    )


def render_workspace(request, template, status=200, **context):
    return render(
        request,
        'users/' + template,
        dict(context, matching_tab=True, dashboard_language=selected_language(request)),
        status=status,
    )


def queue(request):
    tracking = request.GET.get('view') == 'conversations'
    allowed = access.enabled() and access.can_view_pairs(request.user)
    entries = []
    if allowed:
        entries = (
            open_conversations().order_by('-created_at', '-pk')
            if tracking
            else pending_pairs().order_by('-score', 'pk')
        )
    page = Paginator(entries, 20).get_page(request.GET.get('page'))
    matchings = []
    if allowed and not tracking:
        evaluations = MatchEvaluation.objects.in_bulk(
            pair.evaluation_id for pair in page
        )
        matchings = [
            matching_context(request, pair, evaluations[pair.evaluation_id])
            for pair in page
            if pair.evaluation_id in evaluations
        ]
    return render_workspace(
        request,
        'adviser_matching_queue.html',
        matchings=matchings,
        page=page,
        tracking=tracking,
        allowed=allowed,
    )


@transaction.atomic
def record_review(user, pair, evaluation_id, action):
    pair = CandidateOfferMatch.objects.select_for_update().get(pk=pair.pk)
    if pair.decision != 'pending':
        raise services.StaleEvaluation
    if action == 'refresh':
        services.calculate(pair.candidate, pair.offer)
        return
    push_preview = (
        action == 'retained'
        and preview_push.available()
        and pair.candidate.user.email
        in {account['email'] for account in PWA_ACCOUNTS.values()}
    )
    if (
        push_preview
        and not PreviewPushSubscription.objects.filter(
            candidate=pair.candidate
        ).exists()
    ):
        raise ValidationError(
            _('Enable notifications on the test candidate’s phone first.')
        )
    if action == 'retained' and not dialogue_services.enabled():
        raise ValidationError(_('Albert is currently unavailable. Try again later.'))
    services.decide(pair.pk, evaluation_id, action, actor=f'adviser:{user.pk}')
    if action == 'retained':
        confirmation, created = CandidateOfferReview.objects.get_or_create(
            pair=pair, defaults={'requested_by': user}
        )
        if push_preview and created:
            transaction.on_commit(lambda: preview_push.notify(confirmation))


@never_cache
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    access.guard(request)
    language = selected_language(request)
    with translation.override(language):
        pair = get_object_or_404(pending_pairs(), pk=pk)
        evaluation = get_object_or_404(MatchEvaluation, pk=pair.evaluation_id)
        status, error = 200, ''
        if request.method == 'POST':
            form = ReviewForm(request.POST)
            try:
                if not form.is_valid():
                    raise ValidationError(_('Select a valid matching decision.'))
                action = form.cleaned_data['action']
                record_review(
                    request.user, pair, form.cleaned_data['evaluation'], action
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
            matching=matching_context(request, pair, evaluation),
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


def matching_context(request, pair, evaluation):
    language = selected_language(request)
    try:
        stale = evaluation.fingerprint != services.inputs(pair)[1]
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
        pair=pair,
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
            for reference in pair.candidate.occupation_references
            if (occupation := resolve_reference(reference, language))
        ],
        languages=[
            (language_label(row['code']), row['level'])
            for row in pair.candidate.language_skills.get('languages', [])
        ],
        stale=stale,
        can_decide=access.can_change_pair(request.user),
        albert_available=dialogue_services.enabled(),
    )


@never_cache
@require_GET
def follow(request, pk):
    access.guard(request)
    with translation.override(selected_language(request)):
        conversation = get_object_or_404(open_conversations(), pk=pk)
        state = confirmation_services.review(conversation)
        return render_workspace(
            request,
            'adviser_conversation.html',
            conversation=conversation,
            tracking=True,
            pair=conversation.pair,
            rows=display_rows(state['rows'], selected_language(request)),
        )
