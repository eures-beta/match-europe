from django.conf import settings
from django.utils.translation import gettext


def shared_notice():
    if getattr(settings, "SHARED_DEMO", False):
        return gettext(
            "Shared demonstration: fictional data only. External saving and Push diagnostics are disabled."
        )
    return ""
