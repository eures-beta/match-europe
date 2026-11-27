"""Shared follow-up and deliberate, single-recipient reminders."""

from eures_beta.matching.models import MatchEvent
from datetime import timedelta
import hashlib
import json
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from sesame.utils import get_query_string

from eures_beta.emails.rendering import html_email
from eures_beta.users.email_login import email_ready
from eures_beta.matching import access
from eures_beta.introductions import employer_consent, offer_review_services
from eures_beta.introductions.models import (
    CandidateOfferConversation,
    CandidateOfferReview,
    EmployerCandidateReview,
)
from eures_beta.followup.models import (
    MatchFollowup,
    MatchConclusion,
)


class Changed(Exception):
    pass


class RetryLater(Exception):
    pass


def reviews():
    # Keep already-started cases visible even when an offer is no longer matchable.
    return CandidateOfferReview.objects.select_related(
        'match__candidate__user',
        'match__offer__employer',
        'assigned_to_adviser',
        'match__followup',
    )


def context(review):
    state = offer_review_services.review_state(review)
    plan = MatchFollowup.objects.filter(match=review.match).first()
    thread = CandidateOfferConversation.objects.filter(offer_review=review).first()
    agreement = employer_consent.eligible_agreement(state)
    consent = (
        EmployerCandidateReview.objects.filter(agreement=agreement).first()
        if agreement
        else None
    )
    eligible = (
        review.match.decision == 'retained'
        and review.workflow_state != 'refused'
        and not state['declined']
        and access.candidates().filter(pk=review.match.candidate_id).exists()
        and access.matchable_offers().filter(pk=review.match.offer_id).exists()
    )
    recipients = {}
    stage = _('Awaiting candidate replies')
    waiting = 'candidate'
    if not eligible:
        stage, waiting = _('Review the dossier before continuing'), 'adviser'
    elif review.workflow_state == 'clarify':
        stage, waiting = _('Additional candidate information awaited'), 'candidate'
        recipients['candidate'] = (
            review.match.candidate.user,
            'candidate_offer_confirmation',
            review.pk,
        )
    elif thread and thread.state == 'open':
        if (
            thread.candidate_id == review.match.candidate.user_id
            and thread.employer_id == review.match.offer.employer_id
            and employer_consent.introduction_consent(
                review, state, review.assigned_to_adviser
            )
        ):
            stage, waiting = _('Three-person conversation open'), 'adviser'
            recipients = {
                role: (getattr(thread, role), 'shared_conversation', thread.pk)
                for role in ('candidate', 'employer')
            }
        else:
            stage, waiting = _('Review the dossier before continuing'), 'adviser'
    elif (
        consent
        and consent.decision == 'pending'
        and employer_consent.can_prepare(review, state, review.assigned_to_adviser)
    ):
        stage, waiting = _('Awaiting employer response'), 'employer'
        employer = review.match.offer.employer
        if (
            employer
            and employer.is_active
            and employer.kind == 'employer'
            and consent.employer_id == employer.pk
        ):
            recipients['employer'] = (employer, 'respond_employer_consent', consent.pk)
    elif consent and consent.decision in ('declined', 'clarify'):
        stage, waiting = consent.get_decision_display(), 'adviser'
    elif review.workflow_state in ('ready', 'claimed', 'validated'):
        stage, waiting = _('Adviser action needed'), 'adviser'
    else:
        recipients['candidate'] = (
            review.match.candidate.user,
            'candidate_offer_dialogue',
            review.pk,
        )
    if plan and plan.outcome != 'open':
        recipients = {}
    if MatchConclusion.objects.filter(match=review.match).exists():
        recipients = {}
    waiting_since = None
    if plan:
        for event in plan.events.filter(action='plan').order_by('-pk'):
            if any(
                event.snapshot.get(key) != str(getattr(plan, key))
                for key in ('next_action', 'waiting_for', 'outcome')
            ):
                break
            waiting_since = event.created_at
    latest_message = thread.messages.order_by('-pk').first() if thread else None
    latest_event = review.events.order_by('-version').first()
    latest_answer = review.answers.order_by('-pk').first()
    dates = [
        review.created_at,
        review.email_sent_at,
        latest_message.created_at if latest_message else None,
        latest_event.created_at if latest_event else None,
        latest_answer.created_at if latest_answer else None,
        consent.decided_at or consent.created_at if consent else None,
        plan.updated_at if plan else None,
    ]
    stamp = hashlib.sha256(
        json.dumps(
            [
                state['fingerprint'],
                state['agreement'].pk if state['agreement'] else None,
                review.workflow_version,
                review.workflow_state,
                review.match.decision,
                review.match.candidate.user_id,
                review.match.offer.employer_id,
                plan.version if plan else 0,
                thread.pk if thread else None,
                latest_message.pk if latest_message else None,
                consent.pk if consent else None,
                consent.decision if consent else None,
                consent.replies if consent else None,
                sorted(recipients),
            ]
        ).encode()
    ).hexdigest()
    return dict(
        plan=plan,
        stage=stage,
        waiting=waiting,
        recipients=recipients,
        stamp=stamp,
        last_activity=max(date for date in dates if date),
        waiting_since=waiting_since,
        due=bool(
            plan
            and plan.outcome == 'open'
            and plan.due_on
            and plan.due_on <= timezone.localdate()
        ),
    )


def locked_review(adviser, pk):
    if not access.can_change_match(adviser):
        raise PermissionDenied
    review = reviews().get(pk=pk)
    employer_consent.lock_review_scope(review)
    return reviews().select_for_update(of=('self',)).get(pk=pk)


def reminder(adviser, pk, stamp, recipient, message, language='fr'):
    """Claim once before transport. No automatic retry on ambiguous SMTP failures."""
    message = message.strip()
    if not message or len(message) > 2000:
        raise ValidationError(_('Enter a reminder message.'))
    with transaction.atomic():
        review = locked_review(adviser, pk)
        current = context(review)
        if current['stamp'] != stamp:
            raise Changed
        if recipient not in current['recipients']:
            raise ValidationError(_('This person cannot be reminded at this stage.'))
        followup = current['plan']
        if not followup:
            followup = MatchFollowup.objects.create(
                match=review.match,
                next_action=str(_('Follow up on this matching')),
                waiting_for=recipient,
                updated_by_adviser=adviser,
            )
        if followup.events.filter(
            action='reminder', created_at__gt=timezone.now() - timedelta(seconds=60)
        ).exists():
            raise RetryLater
        user, route, target = current['recipients'][recipient]
        if not user.is_active or user.kind != recipient:
            raise Changed
        event = MatchEvent.objects.create(
            match=followup.match,
            kind=MatchEvent.Kind.FOLLOWUP,
            actor=adviser,
            action='reminder',
            recipient=recipient,
            message=message,
            delivery_status='sending' if email_ready() else 'disabled',
        )
        followup.version += 1
        followup.updated_by_adviser = adviser
        followup.save(update_fields=['version', 'updated_by_adviser', 'updated_at'])
    if event.delivery_status == 'disabled':
        return event
    if language not in ('fr', 'en', 'de'):
        language = 'fr'
    destination = reverse(route, args=[target]) + '?' + urlencode({'lang': language})
    link = (
        settings.LOGIN_EMAIL_ORIGIN.rstrip('/')
        + reverse('magic_confirm')
        + get_query_string(user)
        + '&'
        + urlencode({'next': destination})
    )
    try:
        with translation.override(language):
            subject = _('A reminder from your Match Europe adviser')
            body = message + '\n\n' + str(_('Open your dossier')) + '\n' + link
            delivered = (
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_email(
                        body,
                        subject=subject,
                        link=link,
                        action_label=_('Open your dossier'),
                    ),
                )
                == 1
            )
    except Exception:
        delivered = False
    event.delivery_status = 'sent' if delivered else 'failed'
    event.save(update_fields=['delivery_status'])
    return event


def draft(role):
    if role == 'employer':
        return _(
            'Hello, I am following up on the next step in your recruitment. Could you reply in your dossier so that we can move forward? Thank you.'
        )
    return _(
        'Hello, I am following up on your next step with Match Europe. Could you reply in your dossier, or tell me if you need help? Thank you.'
    )
