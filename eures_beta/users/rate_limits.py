"""Shared PostgreSQL limits; no raw address or IP is kept in the buckets."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import LoginRateLimit


def allow_request(request, email):
    now = timezone.now()
    # Delete expired buckets, including unknown addresses. IP is the direct peer;
    # arbitrary forwarded headers are deliberately not trusted.
    LoginRateLimit.objects.filter(expires__lte=now).delete()
    limits = [('ip', request.META.get('REMOTE_ADDR', ''), 30), ('email', email, 5)]
    with transaction.atomic():
        for kind, value, maximum in limits:
            key = salted_hmac('magic-login-rate', kind + ':' + value).hexdigest()
            bucket, _ = LoginRateLimit.objects.select_for_update().get_or_create(
                key=key, defaults={'expires': now + timedelta(minutes=15)}
            )
            if bucket.attempts >= maximum:
                return False
            bucket.attempts += 1
            bucket.save(update_fields=['attempts'])
    return True
