from eures_beta.notifications.services import notify
import hashlib
import secrets
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from eures_beta.notifications.models import Notification
from eures_beta.documents.models import Document
from eures_beta.candidates.models import Candidate
from .models import AccessToken, Event, Match, Offer


def audit(actor, action, obj):
    Event.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        object_type=obj._meta.model_name,
        object_id=obj.pk,
    )


def invite_for(user):
    return signing.dumps({'adviser': user.pk}, salt='me-invitation')


def adviser_from(token):
    try:
        data = signing.loads(token, salt='me-invitation', max_age=90 * 86400)
        return User.objects.get(
            pk=data['adviser'], profile__role='adviser', is_active=True
        )
    except (signing.BadSignature, User.DoesNotExist, KeyError, ValueError):
        return None


def issue_token(user):
    now = timezone.now()
    if AccessToken.objects.filter(
        user=user, created__gt=now - timedelta(seconds=60)
    ).exists():
        return None
    raw = secrets.token_urlsafe(32)
    AccessToken.objects.create(
        user=user,
        digest=hashlib.sha256(raw.encode()).hexdigest(),
        expires=now + timedelta(minutes=15),
    )
    return raw


@transaction.atomic
def consume_token(raw):
    token = (
        AccessToken.objects.select_for_update()
        .filter(
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            used=False,
            expires__gt=timezone.now(),
        )
        .first()
    )
    if not token or not token.user.is_active:
        return None
    token.used = True
    token.save(update_fields=['used'])
    profile = token.user.profile
    profile.verified = True
    profile.save(update_fields=['verified'])
    audit(token.user, 'email_verified', profile)
    for offer in token.user.offers.filter(state=Offer.State.PENDING):
        dispatch_offer(offer, token.user)
    candidate = Candidate.objects.filter(
        user=token.user, validated_at__isnull=False, sent_at__isnull=True
    ).first()
    if candidate:
        candidate.sent_at = timezone.now()
        candidate.save(update_fields=['sent_at'])
        audit(token.user, 'demo_profile_dispatched', candidate)
    return token.user


def dispatch_offer(offer, actor):
    """Offline adapter: does not call AGLAE or start a qualification."""
    if not offer.validated_at or not offer.employer.profile.verified:
        raise ValueError(_('Validate the offer and confirm your email first.'))
    if offer.sent_at:
        return
    offer.sent_at = timezone.now()
    offer.state = Offer.State.SYNCED
    offer.save(update_fields=['state', 'sent_at'])
    audit(actor, 'demo_offer_dispatched', offer)
    Notification.objects.create(
        user=offer.adviser, label='New validated offer', url=f'/offers/{offer.pk}/'
    )


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
                'explanation': 'Demonstration suggestion: no AGLAE score. Review skills, languages, mobility and availability.'
            },
        )
        if created:
            audit(actor, 'demo_match_suggested', match)
