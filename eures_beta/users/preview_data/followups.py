"""Fictional plans only: never sends a reminder or changes an explored plan."""

from datetime import timedelta

from django.utils import timezone

from eures_beta.followup import match_followup as followup, match_lifecycle
from eures_beta.followup.models import MatchFollowup


def seed_followups(adviser, identifiers):
    scenarios = (
        (
            'approved',
            'employer',
            -2,
            '[Fictif] Recueillir la réponse employeur',
        ),
        (
            'clarify',
            'candidate',
            3,
            '[Fictif] Préciser la disponibilité du candidat',
        ),
    )
    for key, waiting, days, action in scenarios:
        review = followup.reviews().filter(match__offer_id=identifiers(key)).first()
        if review is None or MatchFollowup.objects.filter(match=review.match).exists():
            continue
        match_lifecycle.schedule(
            adviser,
            review.match_id,
            version=0,
            next_action=action,
            waiting_for=waiting,
            due_on=timezone.localdate() + timedelta(days=days),
        )

    review = followup.reviews().filter(match__offer_id=identifiers('closed')).first()
    if review and not hasattr(review.match, 'conclusion'):
        match_lifecycle.conclude(
            adviser,
            review.match_id,
            'stopped',
            0,
            reason='[Fictif] Recrutement arrêté après examen du dossier.',
        )
