"""Explicit team grants; invitation permissions and superuser flags grant nothing here."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef
from django.http import Http404
from .access import enabled, local_guard, candidates, offers
from .models import MatchingTeam, TeamMembership, TeamCandidate, TeamOffer, MatchPair


def team_enabled():
    return settings.MATCHING_TEAMS_ENABLED and enabled()


def guard(request):
    require_matching_enabled()
    if not settings.MATCHING_TEAMS_ENABLED:
        raise Http404
    if not request.user.is_active or request.user.kind != 'adviser':
        raise PermissionDenied


def memberships(user):
    if not user.is_authenticated or not user.is_active or user.kind != 'adviser':
        return TeamMembership.objects.none()
    return TeamMembership.objects.filter(
        user_id=user.pk,
        user__is_active=True,
        user__kind='adviser',
        active=True,
        team__active=True,
    )


def team_candidates(team):
    return candidates().filter(
        pk__in=TeamCandidate.objects.filter(team=team).values('candidate_id')
    )


def team_offers(team):
    return offers().filter(
        pk__in=TeamOffer.objects.filter(team=team).values('offer_id')
    )


def pairs(user):
    return (
        MatchPair.objects.filter(
            team_id__in=memberships(user).values('team_id'),
            candidate__in=candidates(),
            offer__in=offers(),
        )
        .annotate(
            offer_access=Exists(
                TeamOffer.objects.filter(
                    team_id=OuterRef('team_id'), offer_id=OuterRef('offer_id')
                )
            ),
            candidate_access=Exists(
                TeamCandidate.objects.filter(
                    team_id=OuterRef('team_id'), candidate_id=OuterRef('candidate_id')
                )
            ),
        )
        .filter(offer_access=True, candidate_access=True)
    )


def require_member(user, team_id, *, decide=False, lock=False):
    if not team_enabled() or not user.is_authenticated:
        raise PermissionDenied
    users = get_user_model().objects
    if lock:
        users = users.select_for_update()
    if not users.filter(pk=user.pk, is_active=True, kind='adviser').exists():
        raise PermissionDenied
    query = memberships(user).filter(team_id=team_id)
    if lock:
        query = query.select_for_update(of=('self', 'team')).select_related('team')
    member = query.first()
    if member is None or (decide and not member.can_decide):
        raise PermissionDenied
    return member
