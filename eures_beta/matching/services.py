from eures_beta.accounts.services import audit
from django.utils.translation import gettext_noop
from django.utils.translation import gettext as _
from eures_beta.candidates.models import Candidate
from eures_beta.matching.models import Match


def suggest_candidates(offer, actor):
    """Demonstration only. No score, ranking or claim of AGLAE matching."""
    if not offer.sent_at:
        raise ValueError(_('Validate the offer and confirm your email first.'))
    for candidate in Candidate.objects.filter(
        sent_at__isnull=False, user__profile__verified=True
    ):
        match, created = Match.objects.get_or_create(
            offer=offer,
            candidate=candidate,
            defaults={
                'explanation': gettext_noop(
                    'Demonstration suggestion: no AGLAE score. Review skills, languages, mobility and availability.'
                )
            },
        )
        if created:
            audit(actor, 'demo_match_suggested', match)
