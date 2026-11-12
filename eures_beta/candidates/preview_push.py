"""Web Push for disposable candidate previews."""

import base64
import binascii
import hashlib
import hmac
import json
import logging
from urllib.parse import urlencode, urlsplit

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.translation import override
from django.views.decorators.http import require_POST
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from eures_beta.matching.confirmation_services import questions, short_question
from eures_beta.users.test_accounts import enabled, fictional_database
from .models import PreviewPushSubscription
from .registration_views import owned_profile

logger = logging.getLogger(__name__)
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def available():
    return (
        settings.DJANGO_ENVIRONMENT == 'preview' and enabled() and fictional_database()
    )


def private_key():
    seed = hmac.digest(
        settings.SECRET_KEY.encode(), b'match-europe-preview-push-v1', hashlib.sha256
    )
    return ec.derive_private_key(
        int.from_bytes(seed) % (P256_ORDER - 1) + 1, ec.SECP256R1()
    )


def public_key():
    value = (
        private_key()
        .public_key()
        .public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    )
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def valid_endpoint(endpoint):
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        return False
    try:
        url = urlsplit(endpoint)
        host = url.hostname or ''
        return (
            url.scheme == 'https'
            and url.netloc == host
            and bool(url.path)
            and not url.fragment
            and (
                host
                in {
                    'fcm.googleapis.com',
                    'updates.push.services.mozilla.com',
                    'web.push.apple.com',
                }
                or host.endswith('.push.apple.com')
            )
        )
    except ValueError:
        return False


def key_bytes(value, size):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError
    raw = base64.b64decode(
        value + '=' * (-len(value) % 4), altchars=b'-_', validate=True
    )
    if len(raw) != size:
        raise ValueError
    return raw


@require_POST
@login_required
def subscribe(request):
    if not available():
        raise Http404
    profile = owned_profile(request)
    if len(request.body) > 4096:
        return JsonResponse({'ok': False}, status=400)
    try:
        data = json.loads(request.body)
        endpoint, keys = data['endpoint'], data['keys']
        if not valid_endpoint(endpoint):
            raise ValueError
        ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), key_bytes(keys['p256dh'], 65)
        )
        key_bytes(keys['auth'], 16)
    except (ValueError, TypeError, KeyError, binascii.Error):
        return JsonResponse({'ok': False}, status=400)
    try:
        with transaction.atomic():
            PreviewPushSubscription.objects.filter(endpoint=endpoint).exclude(
                candidate=profile
            ).delete()
            PreviewPushSubscription.objects.update_or_create(
                candidate=profile,
                defaults={
                    'endpoint': endpoint,
                    'keys': {name: keys[name] for name in ('p256dh', 'auth')},
                },
            )
    except IntegrityError:
        return JsonResponse({'ok': False}, status=409)
    return JsonResponse({'ok': True})


class PushSession(requests.Session):
    def post(self, url, **kwargs):
        return super().post(url, allow_redirects=False, **kwargs)


def notification_payload(confirmation):
    url = reverse('candidate_offer_dialogue', args=[confirmation.pk])
    payload = {'url': url}
    for row in questions(confirmation):
        prompt = short_question(row)
        if prompt:
            payload['url'] = (
                f"{url}?{urlencode({'question': row['key']})}#question-title"
            )
            with override(confirmation.pair.candidate.language):
                payload['body'] = str(prompt)
            break
    return payload


def notify(confirmation):
    subscription = PreviewPushSubscription.objects.filter(
        candidate=confirmation.pair.candidate
    ).first()
    if not subscription or not valid_endpoint(subscription.endpoint):
        return
    key = Vapid(private_key())
    try:
        with PushSession() as session:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': subscription.keys,
                },
                data=json.dumps(notification_payload(confirmation)),
                vapid_private_key=key,
                vapid_claims={'sub': 'https://' + settings.ALLOWED_HOSTS[0]},
                requests_session=session,
                ttl=300,
                timeout=5,
            )
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            PreviewPushSubscription.objects.filter(
                pk=subscription.pk, endpoint=subscription.endpoint
            ).delete()
        logger.warning('Preview candidate push failed (status=%s).', status)
    except (requests.RequestException, ValueError):
        logger.warning('Preview candidate push could not be sent.')
