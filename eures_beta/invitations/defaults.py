from datetime import timedelta
from django.conf import settings
from django.utils import timezone


def invitation_expiry():
    return timezone.now() + timedelta(seconds=settings.INVITATION_MAX_AGE)
