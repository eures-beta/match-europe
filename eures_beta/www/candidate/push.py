"""HTTP registration of a disposable-preview Push subscription."""

import binascii
import json
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from eures_beta.candidates.models import PreviewPushSubscription
from eures_beta.candidates.preview_push import available, valid_endpoint, key_bytes
from .registration import owned_profile


@require_POST
@login_required
def subscribe(request):
    if not available():
        raise Http404
    profile = owned_profile(request)
    from cryptography.hazmat.primitives.asymmetric import ec

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
