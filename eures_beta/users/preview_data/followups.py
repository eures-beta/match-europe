"""Fictional plans only: never sends a reminder or changes an explored plan."""

from datetime import timedelta

from django.utils import timezone

from eures_beta.matching import match_followup as followup
from eures_beta.matching.models import MatchFollowup


def seed_followups(adviser, identifiers):
    scenarios = (
        (
            'approved',
            'employer',
            -2,
            'open',
            '[Fictif] Recueillir la réponse employeur',
            '',
        ),
        (
            'clarify',
            'candidate',
            3,
            'open',
            '[Fictif] Préciser la disponibilité du candidat',
            '',
        ),
        (
            'closed',
            'adviser',
            0,
            'stopped',
            '[Fictif] Clôturer le suivi',
            '[Fictif] Le dossier a été clos par le conseiller.',
        ),
    )
    for key, waiting, days, outcome, action, reason in scenarios:
        review = followup.reviews().filter(match__offer_id=identifiers(key)).first()
        if review is None or MatchFollowup.objects.filter(match=review.match).exists():
            continue
        followup.plan(
            adviser,
            review.pk,
            followup.context(review)['stamp'],
            next_action=action,
            waiting_for=waiting,
            due_on=timezone.localdate() + timedelta(days=days),
            outcome=outcome,
            closure_reason=reason,
        )
    from eures_beta.matching import match_lifecycle

    review = followup.reviews().filter(match__offer_id=identifiers('closed')).first()
    if review and not hasattr(review.match, 'conclusion'):
        match_lifecycle.conclude(
            adviser,
            review.match_id,
            'stopped',
            0,
            reason='[Fictif] Recrutement arrêté après examen du dossier.',
        )
