"""Classify external-search work without treating missing calculations as failures."""

from collections import defaultdict
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from . import access, services
from .models import (
    CandidateSupport,
    JobOfferSupport,
    CandidateOfferMatch,
    MatchEvaluation,
)

REASONS = {
    'no_candidates': _(
        'No eligible candidate is available. Search your internal tools and network.'
    ),
    'no_offers': _(
        'No eligible offer is available. Look for employers and new offers.'
    ),
    'none': _('No suitable matching found. Start an external search.'),
    'refused': _('All proposed matchings were rejected. Continue the external search.'),
    'pending': _(
        'Matching calculation is missing or out of date. No conclusion is available yet.'
    ),
    'incomplete': _(
        'Information is insufficient. Check the record before starting an external search.'
    ),
}


def current(evaluation, match):
    if not evaluation:
        return False
    _, fingerprint = services.snapshot(match, match.candidate, match.offer)
    return evaluation.fingerprint == fingerprint


def classify(pairs, expected, ready, empty_reason):
    if not ready:
        return 'incomplete'
    # A retained dossier is already being followed, even after its inputs change.
    if any(pair.decision == 'retained' for pair, evaluation, fresh in pairs):
        return None
    if any(
        pair.decision == 'pending'
        and evaluation
        and evaluation.result.get('status') == 'review'
        for pair, evaluation, fresh in pairs
    ):
        return None
    if not expected:
        return empty_reason
    if len(pairs) != expected or any(not fresh for pair, evaluation, fresh in pairs):
        return 'pending'
    if all(pair.decision == 'refused' for pair, evaluation, fresh in pairs):
        return 'refused'
    if any(
        evaluation.result.get('status') == 'insufficient'
        for pair, evaluation, fresh in pairs
        if pair.decision != 'refused'
    ):
        return 'incomplete'
    return 'none'


def search_rows():
    candidates = list(access.candidates().order_by('created_at', 'pk'))
    offers = list(access.employer_offers().order_by('created', 'pk'))
    ready_ids = set(access.matchable_offers().values_list('pk', flat=True))
    by_candidate, by_offer = defaultdict(list), defaultdict(list)
    latest = MatchEvaluation.objects.filter(match_id=OuterRef('pk')).order_by('-pk')
    pairs = list(
        CandidateOfferMatch.objects.filter(
            candidate__in=candidates, offer_id__in=ready_ids
        )
        .select_related('candidate', 'offer')
        .annotate(evaluation_id=Subquery(latest.values('pk')[:1]))
    )
    evaluations = MatchEvaluation.objects.in_bulk(
        pair.evaluation_id for pair in pairs if pair.evaluation_id
    )
    for pair in pairs:
        evaluation = evaluations.get(pair.evaluation_id)
        item = (pair, evaluation, current(evaluation, pair))
        by_candidate[pair.candidate_id].append(item)
        by_offer[pair.offer_id].append(item)
    offer_followups = {
        row.job_offer_id: row
        for row in JobOfferSupport.objects.select_related('updated_by')
    }
    candidate_followups = {
        row.candidate_profile_id: row
        for row in CandidateSupport.objects.select_related('updated_by')
    }

    def rows(objects, kind):
        for obj in objects:
            is_offer = kind == 'offers'
            reason = classify(
                by_offer[obj.pk] if is_offer else by_candidate[obj.pk],
                len(candidates) if is_offer else len(ready_ids),
                obj.pk in ready_ids if is_offer else True,
                'no_candidates' if is_offer else 'no_offers',
            )
            if reason is None:
                continue
            followup = (offer_followups if is_offer else candidate_followups).get(
                obj.pk
            )
            yield dict(
                object=obj,
                kind=kind,
                reason=reason,
                explanation=REASONS[reason],
                title=(
                    (obj.data.get('title') or _('Untitled offer'))
                    if is_offer
                    else obj.display_name
                ),
                subtitle=(
                    (obj.data.get('companyName') or '')
                    if is_offer
                    else obj.desired_occupations
                ),
                entered_at=obj.created if is_offer else obj.created_at,
                followup=followup,
                due=bool(
                    followup
                    and followup.follow_up_on
                    and followup.follow_up_on <= timezone.localdate()
                ),
                actionable=reason not in ('pending', 'incomplete'),
            )

    def ordered(entries):
        return sorted(
            entries,
            key=lambda row: (
                not row['due'],
                bool(row['followup'] and row['followup'].is_searching),
                row['entered_at'],
                str(row['object'].pk),
            ),
        )

    return {
        'offers': ordered(rows(offers, 'offers')),
        'candidates': ordered(rows(candidates, 'candidates')),
    }
