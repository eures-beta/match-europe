"""Shared email presentation; business messages and delivery remain separate."""

from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import translation

from .origins import validate_origin


def presentation_context(origin):
    """Use the existing partner assets and a caller-validated public origin."""
    return {
        "privacy": origin + reverse("privacy") if origin else "",
        "partner_logos": [
            (urljoin(origin + "/", static(filename)), label, width)
            for filename, label, width in (
                (
                    "employer/assets/eures-ela.jpg",
                    "EURES / European Labour Authority",
                    112,
                ),
                ("invitations/assets/france-travail-email.png", "France Travail", 88),
                ("employer/assets/adem.png", "ADEM", 34),
                ("employer/assets/forem.png", "Le Forem", 80),
            )
        ],
    }


def html_email(body, *, language=None, subject="", link="", action_label=""):
    """Escape message text and turn complete URLs into explicit HTML anchors."""
    with translation.override(language or translation.get_language()):
        lines = body.split('\n', 1)
        if subject and len(lines) == 2 and lines[0] == subject:
            # The plain alternative keeps its heading; HTML displays it as h1.
            body = lines[1].lstrip('\n')
        context = {
            "body": body,
            "subject": subject,
            "link": link,
            "action_label": action_label,
        }
        try:
            origin = validate_origin(settings.LOGIN_EMAIL_ORIGIN)
        except ValidationError:
            # Pure rendering is also used without a configured delivery origin.
            # Never invent a public host or use a request's Host header.
            pass
        else:
            context.update(presentation_context(origin))
        return render_to_string("emails/message.html", context)
