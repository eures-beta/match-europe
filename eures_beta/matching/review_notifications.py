"""Minimal emails complement durable in-app review events, without internal notes."""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from eures_beta.users.email_login import email_ready
from eures_beta.emails.rendering import html_email
from .models import CandidateOfferReviewEvent

logger = logging.getLogger(__name__)


def send(pk):
    event = CandidateOfferReviewEvent.objects.select_related(
        'review__requested_by_adviser', 'review__match__candidate__user'
    ).get(pk=pk)
    review = event.review
    submitted = event.action in {'submitted', 'candidate_reply'}
    recipient = (
        review.requested_by_adviser if submitted else review.match.candidate.user
    )
    if (
        not recipient.is_active
        or recipient.kind != ('adviser' if submitted else 'candidate')
        or not email_ready()
    ):
        event.delivery_status = 'disabled'
    else:
        language = review.match.candidate.language
        language = language if language in {'fr', 'en', 'de'} else 'fr'
        route = 'adviser_conversation' if submitted else 'candidate_offer_confirmation'
        link = (
            settings.LOGIN_EMAIL_ORIGIN.rstrip('/')
            + reverse(route, args=[review.pk])
            + '?lang='
            + language
        )
        try:
            with translation.override(language):
                subject = (
                    _('Candidate replies are ready for review')
                    if submitted
                    else _('An adviser has reviewed your replies')
                )
                body = (
                    _('Open the private review to see the next step.')
                    if submitted
                    else event.public_message
                )
                body += '\n\n' + link
                accepted = (
                    send_mail(
                        subject,
                        body,
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient.email],
                        html_message=html_email(body),
                    )
                    == 1
                )
            event.delivery_status = 'sent' if accepted else 'failed'
        except Exception:
            logger.error('Review notification delivery failed.')
            event.delivery_status = 'failed'
    event.save(update_fields=['delivery_status'])
