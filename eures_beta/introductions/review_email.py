"""Offer-review email: explicit delivery, personal sign-in, no Push or profile sharing."""

import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from sesame.utils import get_query_string

from eures_beta.users.email_login import email_ready
from eures_beta.emails.rendering import html_email
from eures_beta.matching import access
from eures_beta.introductions.models import CandidateOfferReview

logger = logging.getLogger(__name__)


class RetryLater(Exception):
    pass


def send(review_id, *, adviser=None):
    """Claim an attempt before SMTP. Only an adviser can explicitly retry it."""
    if adviser is not None and not access.can_change_match(adviser):
        raise PermissionDenied
    now = timezone.now()
    with transaction.atomic():
        review = (
            CandidateOfferReview.objects.select_for_update(of=('self',))
            .select_related('match__candidate__user', 'match__offer')
            .filter(
                pk=review_id,
                match__decision='retained',
                match__candidate__in=access.candidates(),
                match__offer__in=access.matchable_offers(),
            )
            .exclude(workflow_state='refused')
            .filter(match__conclusion__isnull=True)
            .first()
        )
        if review is None:
            return False
        if adviser is None and review.email_status != 'pending':
            return False
        delay = 300 if review.email_status == 'sending' else 60
        if review.email_attempted_at and review.email_attempted_at > now - timedelta(
            seconds=delay
        ):
            raise RetryLater
        review.email_attempted_at = now
        review.email_status = 'sending' if email_ready() else 'disabled'
        review.save(update_fields=['email_status', 'email_attempted_at'])
    if review.email_status == 'disabled':
        return False
    candidate = review.match.candidate
    language = candidate.language if candidate.language in ('fr', 'en', 'de') else 'fr'
    destination = reverse('candidate_offer_dialogue', args=[review.pk])
    destination += '?' + urlencode({'lang': language})
    link = (
        settings.LOGIN_EMAIL_ORIGIN.rstrip('/')
        + reverse('magic_confirm')
        + get_query_string(candidate.user)
        + '&'
        + urlencode({'next': destination})
    )
    try:
        with translation.override(language):
            body = render_to_string(
                'introductions/offer_review_email.txt',
                {'offer': review.match.offer.data, 'link': link},
            )
            delivered = (
                send_mail(
                    _('An offer of employment might suit you'),
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [candidate.user.email],
                    html_message=html_email(
                        body,
                        subject=_('An offer of employment might suit you'),
                        link=link,
                        action_label=_('Open the private review to see the next step.'),
                    ),
                )
                == 1
            )
    except Exception:
        # Never log recipient, token, body or provider exceptions.
        logger.error('Offer-review email delivery failed.')
        delivered = False
    CandidateOfferReview.objects.filter(
        pk=review.pk, email_status='sending', email_attempted_at=now
    ).update(
        email_status='sent' if delivered else 'failed',
        **({'email_sent_at': timezone.now()} if delivered else {}),
    )
    return delivered
