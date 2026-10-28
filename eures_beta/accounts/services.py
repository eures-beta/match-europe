import hashlib
import secrets
from datetime import timedelta
from django.contrib.auth.models import User
from django.core import signing
from django.db import transaction
from django.utils import timezone
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer
from eures_beta.accounts.models import AccessToken, Event


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
    from eures_beta.offers.services import dispatch_offer

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
