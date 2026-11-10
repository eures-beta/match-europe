from django.core.exceptions import PermissionDenied
from django.db import transaction
from . import services
from .models import MatchPair, MatchingTeam, TeamOffer, TeamCandidate
from .team_access import require_member, team_candidates, team_enabled, team_offers
from .access import candidates, offers


def locked_scope(user, team_id, candidate_id, offer_id):
    member = require_member(user, team_id, decide=True, lock=True)
    if (
        not TeamOffer.objects.select_for_update()
        .filter(team_id=team_id, offer_id=offer_id)
        .exists()
    ):
        raise PermissionDenied
    if (
        not TeamCandidate.objects.select_for_update()
        .filter(team_id=team_id, candidate_id=candidate_id)
        .exists()
    ):
        raise PermissionDenied
    candidate = team_candidates(member.team).filter(pk=candidate_id).first()
    offer = team_offers(member.team).filter(pk=offer_id).first()
    if candidate is None or offer is None:
        raise PermissionDenied
    return member, candidate, offer


@transaction.atomic
def calculate(user, team_id, candidate_id, offer_id, *, manual=False):
    member, candidate, offer = locked_scope(user, team_id, candidate_id, offer_id)
    pair, created = MatchPair.objects.get_or_create(
        candidate=candidate,
        offer=offer,
        defaults={'team': member.team, 'source': 'manual' if manual else 'calculated'},
    )
    pair = MatchPair.objects.select_for_update().get(pk=pair.pk)
    if pair.team_id != member.team_id:
        raise PermissionDenied
    result = services.calculate(candidate, offer)
    result.requested_by = user
    result.request_mode = 'manual' if manual else 'calculated'
    result.save(update_fields=['requested_by', 'request_mode'])
    return result


@transaction.atomic
def decide(
    user, pair_id, evaluation_id, value, *, manual=False, reason='', expected_decision=0
):
    # Read identifiers only before authorizing; no result data escapes this service.
    reference = (
        MatchPair.objects.filter(pk=pair_id)
        .values('team_id', 'candidate_id', 'offer_id')
        .first()
    )
    if not reference or not reference['team_id']:
        raise PermissionDenied
    member, candidate, offer = locked_scope(
        user, reference['team_id'], reference['candidate_id'], reference['offer_id']
    )
    pair = MatchPair.objects.select_for_update().get(pk=pair_id)
    if pair.team_id != member.team_id:
        raise PermissionDenied
    reason = reason.strip()
    if len(reason) > 2000 or (manual and (value != 'retained' or not reason)):
        raise ValueError('A manual proposal requires a reason')
    previous = pair.decisions.order_by('-id').first()
    same_request = bool(
        previous
        and previous.evaluation_id == evaluation_id
        and previous.value == value
        and previous.decided_by_id == user.pk
        and previous.manual == manual
        and previous.reason == reason
    )
    if (previous.pk if previous else 0) != expected_decision and not same_request:
        raise services.StaleEvaluation('Another team member changed the decision')
    return services.decide(
        pair.pk,
        evaluation_id,
        value,
        manual=manual,
        reason=reason,
        decided_by=user,
        team=member.team,
    )


@transaction.atomic
def calculate_for_saved_offer(offer_id, revision):
    if not team_enabled():
        return
    teams = list(
        MatchingTeam.objects.select_for_update().filter(active=True).order_by('pk')[:2]
    )
    if len(teams) != 1:
        return
    team = teams[0]
    offer = offers().filter(pk=offer_id, revision=revision).first()
    if offer is None:
        return
    assignment, _ = TeamOffer.objects.get_or_create(
        offer=offer, defaults={'team': team}
    )
    if assignment.team_id != team.pk:
        return
    for candidate in candidates().order_by('pk'):
        TeamCandidate.objects.get_or_create(team=team, candidate=candidate)
        pair, _ = MatchPair.objects.get_or_create(
            candidate=candidate, offer=offer, defaults={'team': team}
        )
        if pair.team_id is None:
            pair.team = team
            pair.save(update_fields=['team'])
        if pair.team_id == team.pk:
            services.calculate(candidate, offer, reuse_current=True)


def schedule_offer_matching(offer):
    offer_id, revision = offer.pk, offer.revision
    transaction.on_commit(
        lambda: calculate_for_saved_offer(offer_id, revision),
        robust=True,
    )
