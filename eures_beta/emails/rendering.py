"""HTML alternative for transactional messages whose source remains plain text."""

from django.template.loader import render_to_string
from django.utils import translation


def html_email(body, *, language=None):
    """Escape message text and turn complete URLs into explicit HTML anchors."""
    with translation.override(language or translation.get_language()):
        return render_to_string("emails/message.html", {"body": body})
