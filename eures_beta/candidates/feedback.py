"""Team address for candidate problems and suggestions."""

from django.conf import settings


def context(request):
    return {"candidate_feedback_email": settings.CANDIDATE_FEEDBACK_EMAIL}
