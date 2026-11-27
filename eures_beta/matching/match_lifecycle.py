"""One dossier per matching, from calculation to a human-confirmed outcome."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from . import access, employer_consent, offer_review_services, review_workflow
from .models import (
    CandidateOfferMatch,
    CandidateOfferReview,
    CandidateOfferConversation,
    MatchFollowup,
    MatchFollowupEvent,
    MatchConclusion,
    MatchConclusionEvent,
)


class Changed(Exception):
    pass


def matches():
    return CandidateOfferMatch.objects.select_related(
        'candidate__user',
        'offer__employer',
        'conclusion',
        'followup',
        'candidate_offer_review__assigned_to_adviser',
    )


def summary(match):
    review = getattr(match, 'candidate_offer_review', None)
    plan = getattr(match, 'followup', None)
    conclusion = getattr(match, 'conclusion', None)
    decision = match.decisions.order_by('-pk').first()
    thread = (
        CandidateOfferConversation.objects.filter(offer_review=review).first()
        if review
        else None
    )
    state = offer_review_services.review_state(review) if review else None
    agreement = employer_consent.eligible_agreement(state) if state else None
    consent = getattr(agreement, 'employercandidatereview', None) if agreement else None
    validation = (
        review.events.filter(action='validated').order_by('-version').first()
        if review
        else None
    )
    first_message = (
        thread.messages.order_by('pk').first()
        if thread and thread.state == 'open'
        else None
    )
    dates = [
        match.created_at,
        decision.created_at if decision else None,
        agreement.created_at if agreement else thread.consent_at if thread else None,
        validation.created_at if validation else None,
        consent.decided_at if consent and consent.decision == 'accepted' else None,
        first_message.created_at if first_message else None,
        conclusion.declared_at if conclusion else None,
        conclusion.confirmed_at if conclusion else None,
    ]
    labels = [
        _('Matching created'),
        _('Matching examined'),
        _('Candidate agreement'),
        _('Adviser validation'),
        _('Employer agreement'),
        _('Three-person conversation'),
        _('Hiring'),
        _('Matching closed'),
    ]
    index, title, waiting, action = 1, _('Matching to examine'), 'adviser', 'examine'
    stage_since = match.created_at
    closed, stopped = False, False
    reason = ''
    if match.decision == 'refused':
        title, action, closed, stopped = (
            _('Matching declined by an adviser'),
            'none',
            True,
            True,
        )
        reason = title
    elif review:
        stage_since = review.created_at
        index, title, waiting, action = (
            2,
            _('Awaiting candidate replies and permission'),
            'candidate',
            'candidate_reminder',
        )
        if review.workflow_state == 'refused' or state['declined']:
            title, action, waiting, closed, stopped = (
                _('Matching stopped after candidate review'),
                'review',
                'adviser',
                review.workflow_state == 'refused',
                review.workflow_state == 'refused',
            )
            reason = title
        elif agreement:
            stage_since = review.submitted_at or agreement.created_at
            index, title, waiting, action = (
                3,
                _('Candidate replies to validate'),
                'adviser',
                'review',
            )
            if review.workflow_state == 'validated' and review_workflow.current(
                review, state
            ):
                index, title, action = (
                    4,
                    _('Ask for the employer’s agreement'),
                    'prepare_employer',
                )
                if consent:
                    stage_since = consent.decided_at or consent.created_at
                    if consent.decision == 'pending':
                        title, waiting, action = (
                            _('Awaiting employer response'),
                            'employer',
                            'employer_reminder',
                        )
                    elif consent.decision == 'declined':
                        title, action = (
                            _('Employer declined this introduction'),
                            'review',
                        )
                        reason = title
                    elif consent.decision == 'clarify':
                        title, action = (
                            _('Clarify the employer’s reservations'),
                            'review',
                        )
                    elif employer_consent.introduction_consent(
                        review, state, review.assigned_to_adviser
                    ):
                        index, title, action = (
                            5,
                            _('Ready to open the three-person conversation'),
                            'open',
                        )
                        if thread and thread.state == 'open':
                            title, action = (
                                _('Three-person exchange in progress'),
                                'conversation',
                            )
                            stage_since = (
                                first_message.created_at
                                if first_message
                                else stage_since
                            )
        elif state['agreement'] is not None and not state['agreement'].agreed:
            title, waiting, action = (
                _('Candidate permission to clarify'),
                'adviser',
                'review',
            )
    elif match.decision == 'retained':
        title, action, index = _('Offer proposal to prepare'), 'propose', 2
    if thread and thread.state == 'open' and not closed:
        index, title, waiting, action = (
            5,
            _('Three-person exchange in progress'),
            'adviser',
            'conversation',
        )
        stage_since = first_message.created_at if first_message else stage_since
        if (
            not agreement
            or not review_workflow.current(review, state)
            or (consent and consent.decision in ('declined', 'clarify'))
        ):
            title, action = _('Conversation open — conditions to review'), 'review'
    if thread and thread.state == 'declined' and not closed:
        index, title, waiting, action = (
            5,
            _('The candidate declined the shared conversation.'),
            'adviser',
            'review',
        )
    if review and review.workflow_state == 'clarify' and not closed:
        index, title, waiting, action = (
            2,
            _('Additional candidate information awaited'),
            'candidate',
            'candidate_reminder',
        )
        last_request = (
            review.events.filter(action='clarify').order_by('-version').first()
        )
        stage_since = last_request.created_at if last_request else review.created_at
    if not closed and (
        not access.candidates().filter(pk=match.candidate_id).exists()
        or not access.matchable_offers().filter(pk=match.offer_id).exists()
    ):
        title, action, waiting = (
            _('Matching data changed — review needed'),
            'none',
            'adviser',
        )
    if plan and plan.outcome == 'stopped' and not conclusion:
        closed, stopped, title, reason, action = (
            True,
            True,
            _('Matching stopped by an adviser'),
            plan.closure_reason,
            'none',
        )
    if conclusion:
        stage_since = conclusion.updated_at
        index, waiting, reason = 6, 'adviser', conclusion.reason
        if conclusion.state == 'reported':
            title, action = (
                _('Hiring declared — adviser confirmation needed'),
                'confirm',
            )
            closed, stopped = False, False
        else:
            index, title, action, closed = (
                7,
                conclusion.get_state_display(),
                'none',
                True,
            )
            stopped = conclusion.state == 'stopped'
    elif plan and plan.outcome == 'hired':
        # Historical adviser-entered outcome is not an employer hiring declaration.
        title, waiting, action, index = (
            _('Recorded hiring outcome to verify'),
            'adviser',
            'review',
            6,
        )
    milestones = []
    for position, (label, date) in enumerate(zip(labels, dates, strict=True)):
        status = 'done' if date else 'pending'
        if not date and position < index and not stopped:
            status = 'historical'
        if position == index:
            status = 'stopped' if stopped else ('done' if closed else 'current')
        milestones.append(dict(label=label, date=date, status=status))
    if closed:
        milestones[-1]['status'] = 'done'
        if not milestones[-1]['date']:
            milestones[-1]['date'] = (
                plan.updated_at
                if plan and plan.outcome == 'stopped'
                else (
                    decision.created_at
                    if decision and decision.value == 'refused'
                    else None
                )
            )
    latest_dates = [date for date in dates if date]
    if review:
        event = review.events.order_by('-version').first()
        answer = review.answers.order_by('-pk').first()
        latest_dates += [obj.created_at for obj in (event, answer) if obj]
    if thread:
        message = thread.messages.order_by('-pk').first()
        if message:
            latest_dates.append(message.created_at)
    if plan:
        latest_dates.append(plan.updated_at)
    if conclusion:
        latest_dates.append(conclusion.updated_at)
    return dict(
        match=match,
        review=review,
        plan=plan,
        conclusion=conclusion,
        thread=thread,
        stage=title,
        waiting=waiting,
        action=action,
        stage_since=stage_since,
        steps=milestones,
        closed=closed,
        stopped=stopped,
        reason=reason,
        current_step=index + 1,
        last_activity=max(latest_dates),
        due=bool(
            plan and not closed and plan.due_on and plan.due_on <= timezone.localdate()
        ),
        version=conclusion.version if conclusion else 0,
    )


def lock_match(pk):
    match = matches().select_for_update(of=('self',)).get(pk=pk)
    review = getattr(match, 'candidate_offer_review', None)
    if review:
        employer_consent.lock_review_scope(review)
    return matches().get(pk=pk)


def can_report(user, match):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.kind != 'employer'
        or match.offer.employer_id != user.pk
    ):
        return False
    if (
        match.decision != 'retained'
        or MatchFollowup.objects.filter(match=match, outcome='stopped').exists()
    ):
        return False
    return (
        CandidateOfferConversation.objects.filter(
            offer_review__match=match,
            state='open',
            employer=user,
            candidate_id=match.candidate.user_id,
        )
        .exclude(offer_review__workflow_state='refused')
        .exists()
        and not MatchConclusion.objects.filter(match=match).exists()
    )


@transaction.atomic
def conclude(user, pk, action, version, *, start_on=None, reason='', verified=False):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied
    match = lock_match(pk)
    obj = getattr(match, 'conclusion', None)
    if (obj.version if obj else 0) != version:
        raise Changed
    if obj and obj.state in ('hired', 'stopped'):
        raise Changed
    now = timezone.now()
    if action == 'reported':
        if not can_report(user, match):
            raise PermissionDenied
        obj = MatchConclusion(
            match=match, declared_by_employer=user, declared_at=now, start_on=start_on
        )
    elif action == 'hired':
        if not access.can_change_match(user):
            raise PermissionDenied
        if (
            not obj
            or obj.state != 'reported'
            or not verified
            or obj.declared_by_employer_id != match.offer.employer_id
        ):
            raise ValidationError(
                _(
                    'Verify the employer’s hiring declaration before closing this matching.'
                )
            )
        obj.confirmed_by_adviser, obj.confirmed_at = user, now
        obj.start_on = start_on or obj.start_on
    elif action == 'stopped':
        if not access.can_change_match(user):
            raise PermissionDenied
        if not reason.strip():
            raise ValidationError(_('Give a reason for stopping this matching.'))
        obj = obj or MatchConclusion(match=match)
        obj.confirmed_by_adviser, obj.confirmed_at, obj.reason = (
            user,
            now,
            reason.strip(),
        )
    else:
        raise ValidationError(_('Choose a valid matching outcome.'))
    obj.state = action
    obj.version += 1
    obj.full_clean()
    obj.save()
    MatchConclusionEvent.objects.create(
        conclusion=obj,
        actor=user,
        action=action,
        version=obj.version,
        start_on=obj.start_on,
        reason=obj.reason,
    )
    plan = MatchFollowup.objects.filter(match=match).first()
    if plan:
        plan.version += 1
        plan.due_on = None
        if action in ('hired', 'stopped'):
            plan.outcome = action
            plan.closure_reason = (
                str(_('Hiring confirmed by an adviser.'))
                if action == 'hired'
                else reason.strip()
            )
            plan.updated_by_adviser = user
        else:
            plan.waiting_for = 'adviser'
            plan.next_action = str(_('Confirm the declared hiring'))
        plan.save()
    return obj


@transaction.atomic
def schedule(user, pk, *, due_on, version, next_action='', waiting_for='adviser'):
    if not access.can_change_match(user):
        raise PermissionDenied
    match = lock_match(pk)
    current = summary(match)
    if (current['plan'].version if current['plan'] else 0) != version:
        raise Changed
    if current['closed'] or current['conclusion']:
        raise Changed
    if not due_on or waiting_for not in ('adviser', 'candidate', 'employer'):
        raise ValidationError(_('Choose a check-in date and a responsible person.'))
    plan = current['plan'] or MatchFollowup(match=match)
    plan.due_on, plan.waiting_for, plan.next_action = (
        due_on,
        waiting_for,
        next_action.strip() or str(current['stage']),
    )
    plan.updated_by_adviser = user
    plan.version += 1
    plan.full_clean()
    plan.save()
    MatchFollowupEvent.objects.create(
        followup=plan,
        actor=user,
        action='plan',
        snapshot={
            key: str(getattr(plan, key) or '')
            for key in (
                'next_action',
                'waiting_for',
                'due_on',
                'outcome',
                'closure_reason',
            )
        },
    )
    return plan
