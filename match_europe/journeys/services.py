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
from .models import AccessToken, Candidate, Document, Event, Match, Notification, Offer

def audit(actor, action, obj):
    Event.objects.create(actor=actor if actor and actor.is_authenticated else None, action=action, object_type=obj._meta.model_name, object_id=obj.pk)

def invite_for(user):
    return signing.dumps({'adviser': user.pk}, salt='me-invitation')

def adviser_from(token):
    try:
        data = signing.loads(token, salt='me-invitation', max_age=90 * 86400)
        return User.objects.get(pk=data['adviser'], profile__role='adviser', is_active=True)
    except (signing.BadSignature, User.DoesNotExist, KeyError, ValueError):
        return None

def issue_token(user):
    now = timezone.now()
    if AccessToken.objects.filter(user=user, created__gt=now - timedelta(seconds=60)).exists():
        return None
    raw = secrets.token_urlsafe(32)
    AccessToken.objects.create(user=user, digest=hashlib.sha256(raw.encode()).hexdigest(), expires=now + timedelta(minutes=15))
    return raw

@transaction.atomic
def consume_token(raw):
    token = AccessToken.objects.select_for_update().filter(digest=hashlib.sha256(raw.encode()).hexdigest(), used=False, expires__gt=timezone.now()).first()
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
    candidate = Candidate.objects.filter(user=token.user, validated_at__isnull=False, sent_at__isnull=True).first()
    if candidate:
        candidate.sent_at = timezone.now()
        candidate.save(update_fields=['sent_at'])
        audit(token.user, 'demo_profile_dispatched', candidate)
    return token.user

def extract_pdf(upload, user):
    contents = upload.read()
    if len(contents) > 10 * 1024 * 1024:
        raise ValueError('The PDF must be smaller than 10 MB.')
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('pdf_reader.py'))], input=contents, capture_output=True, timeout=15, check=True)
        text = json.loads(result.stdout)['text']
    except Exception as exc:
        raise ValueError('This PDF cannot be read. Use an unencrypted document with at most 30 pages.') from exc
    upload.seek(0)
    upload.name = secrets.token_hex(16) + '.pdf'
    document = Document.objects.create(owner=user, file=upload, text=text)
    audit(user, 'pdf_uploaded', document)
    return document

def dispatch_offer(offer, actor):
    """Offline adapter: does not call AGLAE or start a qualification."""
    if not offer.validated_at or not offer.employer.profile.verified:
        raise ValueError('Validate the offer and confirm your email first.')
    if offer.sent_at:
        return
    offer.sent_at = timezone.now()
    offer.state = Offer.State.SYNCED
    offer.save(update_fields=['state', 'sent_at'])
    audit(actor, 'demo_offer_dispatched', offer)
    Notification.objects.create(user=offer.adviser, label='New validated offer', url=f'/offers/{offer.pk}/')

def suggest_candidates(offer, actor):
    """Demonstration only. No score, ranking or claim of AGLAE matching."""
    if not offer.sent_at:
        raise ValueError('Validate the offer and confirm your email first.')
    for candidate in Candidate.objects.filter(sent_at__isnull=False, user__profile__verified=True):
        match, created = Match.objects.get_or_create(offer=offer, candidate=candidate, defaults={'explanation': 'Demonstration suggestion: no AGLAE score. Review skills, languages, mobility and availability.'})
        if created:
            audit(actor, 'demo_match_suggested', match)

def notify(user, label, url):
    Notification.objects.create(user=user, label=label, url=url)
