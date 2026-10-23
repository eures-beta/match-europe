import os

from django.conf import settings
from django.utils.translation import gettext


def shared_notice():
    if getattr(settings, "SHARED_DEMO", False):
        return gettext(
            "Shared demonstration: fictional data only. External saving and Push diagnostics are disabled."
        )
    return ""


def review_only():
    """Shared demonstrations cannot invoke preparation or geocoding services."""
    return (
        getattr(settings, "SHARED_DEMO", False)
        or os.environ.get("ME_LOCAL_REVIEW_ONLY") == "1"
    )


def employer_email_enabled():
    """Enable simulated email only in an explicitly configured demonstration."""
    return (
        getattr(settings, "SHARED_DEMO", False)
        or os.environ.get("ME_EMPLOYER_EMAIL_LOCAL") == "1"
    )
