"""Durable handoff to the adviser team; all mutations are versioned and locked."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from eures_beta.matching import access
from eures_beta.introductions import offer_review_services as confirmations
from eures_beta.candidates.models import CandidateProfileReviewSuggestion
from eures_beta.introductions.models import (
    CandidateOfferReview,
    CandidateOfferReviewEvent,
)
from eures_beta.matching.services import StaleEvaluation

DECISIONS = {'validated', 'clarify', 'refused'}


def completion(state):
    return bool(state['declined'] or (not state['pending'] and state['agreement']))


def signature(state):
    return confirmations.digest(
        {
            'context': state['fingerprint'],
            'agreement': state['agreement'].pk if state['agreement'] else None,
        }
    )


def current(review, state=None):
    state = state or confirmations.review_state(review)
    return completion(state) and signature(state) == review.submitted_fingerprint


def record(review, actor, action, **kwargs):
    review.workflow_version += 1
    review.save(
        update_fields=[
            'workflow_version',
            'workflow_state',
            'assigned_to_adviser',
            'summary',
            'submitted_fingerprint',
            'submitted_at',
        ]
    )
    return CandidateOfferReviewEvent.objects.create(
        review=review,
        actor=actor,
        version=review.workflow_version,
        action=action,
        **kwargs,
    )


def notify(event):
    # The durable event is the in-app alert, even when transport is disabled/fails.
    from eures_beta.introductions.review_notifications import send

    transaction.on_commit(lambda: send(event.pk))


def sync(review, actor):
    """Caller holds the match, review and profile locks (answer/agree)."""
    review.refresh_from_db()
    state = confirmations.review_state(review)
    if not completion(state):
        if review.workflow_state != 'waiting':
            review.workflow_state = 'waiting'
            review.assigned_to_adviser = None
            record(review, actor, 'reopened')
        return
    if current(review, state):
        return
    review.workflow_state = 'ready'
    review.assigned_to_adviser = None
    review.submitted_at = timezone.now()
    review.submitted_fingerprint = signature(state)
    review.summary = {
        'context': state['fingerprint'],
        'sharing': state['agreement'].agreed if state['agreement'] else None,
        'declined': bool(state['declined']),
        'answers': [
            {
                'key': row['key'],
                'kind': row['kind'],
                'presented': row['presented'],
                'answer_id': row['answer'].pk if row['answer'] else None,
                'value': row['answer'].value if row['answer'] else None,
                'detail': row['answer'].detail if row['answer'] else '',
                'scope': row['answer'].dialogue.get('scope') if row['answer'] else None,
            }
            for row in state['rows']
        ],
    }
    notify(record(review, actor, 'submitted', snapshot=review.summary))


@transaction.atomic
def submit(user, pk, fingerprint, version):
    review = confirmations.locked_review(user, pk)
    state = confirmations.review_state(review)
    if (
        not completion(state)
        or state['fingerprint'] != fingerprint
        or review.workflow_version != version
    ):
        raise StaleEvaluation
    sync(review, user)


@transaction.atomic
def supplement(user, pk, version, text):
    review = confirmations.locked_review(user, pk)
    if (
        review.workflow_version != version
        or review.workflow_state != 'clarify'
        or not current(review)
    ):
        raise StaleEvaluation
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValidationError('Invalid message')
    review.workflow_state = 'claimed' if review.assigned_to_adviser_id else 'ready'
    review.summary = {
        **review.summary,
        'supplements': [*review.summary.get('supplements', []), text.strip()],
    }
    notify(
        record(
            review,
            user,
            'candidate_reply',
            public_message=text.strip(),
            snapshot=review.summary,
        )
    )


@transaction.atomic
def handle(
    user, pk, action, version, fingerprint, *, public_message='', internal_note=''
):
    if not access.can_change_match(user):
        raise PermissionDenied
    # Use the same lock order as candidate replies to serialize handoff and changes.
    review = CandidateOfferReview.objects.select_related('match').get(pk=pk)
    from eures_beta.matching.models import CandidateOfferMatch

    CandidateOfferMatch.objects.select_for_update().get(pk=review.match_id)
    review = (
        CandidateOfferReview.objects.select_for_update(of=('self',))
        .select_related('match__candidate', 'match__offer')
        .get(
            pk=pk,
            match__decision='retained',
            match__candidate__in=access.candidates(),
            match__offer__in=access.matchable_offers(),
        )
    )
    from eures_beta.candidates.models import CandidateProfile
    from eures_beta.employers.models import JobOffer

    CandidateProfile.objects.select_for_update().get(pk=review.match.candidate_id)
    JobOffer.objects.select_for_update().get(pk=review.match.offer_id)
    state = confirmations.review_state(review)
    if (
        version != review.workflow_version
        or fingerprint != state['fingerprint']
        or not current(review, state)
    ):
        raise StaleEvaluation
    if action not in {'claim', 'release', 'takeover', *DECISIONS}:
        raise ValidationError('Invalid action')
    if not all(
        isinstance(value, str) and len(value) <= 2000
        for value in (public_message, internal_note)
    ):
        raise ValidationError('Invalid message')
    public_message, internal_note = public_message.strip(), internal_note.strip()
    if action == 'claim':
        if review.assigned_to_adviser_id or review.workflow_state not in {
            'ready',
            'clarify',
        }:
            raise StaleEvaluation
        review.assigned_to_adviser = user
        if review.workflow_state == 'ready':
            review.workflow_state = 'claimed'
    elif action == 'takeover':
        if (
            not review.assigned_to_adviser_id
            or review.assigned_to_adviser_id == user.pk
            or not internal_note
        ):
            raise StaleEvaluation
        review.assigned_to_adviser = user
    else:
        if review.assigned_to_adviser_id != user.pk:
            raise PermissionDenied
        if action == 'release':
            if review.workflow_state in {'validated', 'refused'}:
                raise StaleEvaluation
            review.assigned_to_adviser = None
            if review.workflow_state != 'clarify':
                review.workflow_state = 'ready'
        elif action in DECISIONS:
            if review.workflow_state not in {'claimed', 'clarify'}:
                raise StaleEvaluation
            if not public_message:
                raise ValidationError('A candidate-facing explanation is required')
            if action == 'validated' and (
                state['declined']
                or not state['agreement']
                or not state['agreement'].agreed
            ):
                raise ValidationError('Transmission permission is required')
            review.workflow_state = action
    event = record(
        review,
        user,
        action,
        public_message=public_message if action in DECISIONS else '',
        internal_note=internal_note,
    )
    if action in DECISIONS:
        notify(event)
    if action == 'takeover':
        from eures_beta.introductions.models import CandidateOfferConversation

        CandidateOfferConversation.objects.filter(offer_review=review).update(
            adviser=user
        )
    return event


def condition_identity(presented):
    if presented['key'] in {'occupation', 'employer'}:
        return None
    expected = presented['expected']
    if isinstance(expected, dict):
        expected = {key: value for key, value in expected.items() if key != 'mandatory'}
    return {'kind': presented['key'], 'expected': expected}


def check_repeated_refusal(event):
    if event.value != 'no':
        return
    identity = condition_identity(event.presented)
    if not identity:
        return
    profile = event.review.match.candidate
    evidence = refusal_evidence(profile, identity)
    if len({item['offer'] for item in evidence}) >= 3:
        prompt, created = CandidateProfileReviewSuggestion.objects.get_or_create(
            candidate=profile,
            condition_hash=confirmations.digest(identity),
            profile_updated_at=profile.updated_at,
            defaults={
                'condition': {**identity, 'presented': event.presented},
                'evidence': evidence,
            },
        )
        if not created and not prompt.resolution:
            prompt.evidence = evidence
            prompt.save(update_fields=['evidence'])


def refusal_evidence(profile, identity):
    # Latest valid answer per offer only. Old preferences and corrected answers do not count.
    evidence = []
    for review in CandidateOfferReview.objects.filter(
        match__candidate=profile
    ).select_related('match__offer', 'match__candidate'):
        state = confirmations.review_state(review)
        for row in state['rows']:
            answer = row['answer']
            if (
                answer
                and answer.value == 'no'
                and condition_identity(answer.presented) == identity
            ):
                evidence.append(
                    {'offer': str(review.match.offer_id), 'answer': answer.pk}
                )
                break
    return evidence


def prompts(review):
    rows = CandidateProfileReviewSuggestion.objects.filter(
        candidate=review.match.candidate,
        profile_updated_at=review.match.candidate.updated_at,
        resolution='',
    )
    valid = [
        row.pk
        for row in rows
        if len(
            refusal_evidence(
                review.match.candidate,
                {key: row.condition[key] for key in ('kind', 'expected')},
            )
        )
        >= 3
    ]
    return rows.filter(pk__in=valid)


@transaction.atomic
def resolve_prompt(user, pk, resolution):
    if not user.is_authenticated or not user.is_active or user.kind != 'candidate':
        raise PermissionDenied
    from eures_beta.candidates.models import CandidateProfile

    profile = CandidateProfile.objects.select_for_update().get(user=user)
    prompt = CandidateProfileReviewSuggestion.objects.select_for_update().get(
        pk=pk, candidate=profile
    )
    if (
        prompt.resolution
        or profile.updated_at != prompt.profile_updated_at
        or resolution not in {'keep', 'review'}
        or len(
            refusal_evidence(
                profile, {key: prompt.condition[key] for key in ('kind', 'expected')}
            )
        )
        < 3
    ):
        raise StaleEvaluation
    prompt.resolution = resolution
    prompt.resolved_at = timezone.now()
    prompt.save(update_fields=['resolution', 'resolved_at'])
    return prompt
