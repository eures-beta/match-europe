"""Web Push for authenticated candidates in every environment."""

import base64
import hashlib
import hmac
import json
import logging
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext, override

from .models import PreviewPushSubscription

logger = logging.getLogger(__name__)
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def available():
    return bool(settings.SECRET_KEY)


def private_key():
    from cryptography.hazmat.primitives.asymmetric import ec

    seed = hmac.digest(
        settings.SECRET_KEY.encode(), b'match-europe-preview-push-v1', hashlib.sha256
    )
    return ec.derive_private_key(
        int.from_bytes(seed) % (P256_ORDER - 1) + 1, ec.SECP256R1()
    )


def public_key():
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

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


class PushSession(requests.Session):
    def post(self, url, **kwargs):
        return super().post(url, allow_redirects=False, **kwargs)


def notification_payload(confirmation):
    with override(confirmation.pair.candidate.language):
        return {
            'url': reverse('candidate_offer_dialogue', args=[confirmation.pk]),
            'body': gettext(
                'An offer might suit you. Tap to see the job and answer a few questions.'
            ),
        }


def notify(confirmation):
    return send(confirmation.pair.candidate, notification_payload(confirmation))


def notify_shared(thread, *, invitation=False):
    candidate = thread.confirmation.pair.candidate
    with override(candidate.language):
        payload = {
            'url': reverse('shared_conversation', args=[thread.pk]),
            'body': (
                gettext('The adviser invites you to join a shared conversation.')
                if invitation
                else gettext('You have a new message in a shared conversation.')
            ),
        }
    return send(candidate, payload)


def send(candidate, payload):
    subscription = PreviewPushSubscription.objects.filter(candidate=candidate).first()
    if not subscription or not valid_endpoint(subscription.endpoint):
        return False
    # Ordinary page loads and catalogue searches do not need the Push SDK.
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush

    key = Vapid(private_key())
    try:
        with PushSession() as session:
            response = webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': subscription.keys,
                },
                data=json.dumps(payload),
                vapid_private_key=key,
                vapid_claims={'sub': 'https://' + settings.ALLOWED_HOSTS[0]},
                requests_session=session,
                ttl=300,
                timeout=5,
            )
        return 200 <= response.status_code < 300
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            PreviewPushSubscription.objects.filter(
                pk=subscription.pk, endpoint=subscription.endpoint
            ).delete()
        logger.warning('Preview candidate push failed (status=%s).', status)
    except (requests.RequestException, ValueError):
        logger.warning('Preview candidate push could not be sent.')
    return False
