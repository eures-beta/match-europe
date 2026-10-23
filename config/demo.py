"""Initialize fictional accounts once, without resetting a preview's existing data."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command


def ensure_demo():
    if settings.DEMO_MODE and getattr(settings, "SHARED_DEMO", False):
        if (
            not get_user_model()
            .objects.filter(username="admin@example.invalid")
            .exists()
        ):
            call_command("seed_demo", verbosity=0)
