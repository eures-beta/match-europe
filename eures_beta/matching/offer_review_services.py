"""Explicit offer-specific confirmations. No inference, profile writes or sending."""

import hashlib
import json
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from . import access
from .models import (
    CandidateOfferMatch,
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
)
from .services import inputs, StaleEvaluation
from .engine import evaluate, DAYS
from .presentation import readable_date

VERSION = 'offer-confirmation-v1'
VALUES = {'yes', 'conditional', 'no', 'changed', 'clarify'}

QUESTION_TEMPLATES = {
    'occupation': _('Could you see yourself doing this job: %(requirement)s?'),
    'employer': _(
        '%(requirement)s is recruiting. Could you see yourself working for them?'
    ),
    'schedule': _('Can you work these hours: %(requirement)s?'),
    'availability': _(
        'Can you start within the timeframe stated in the offer: %(requirement)s?'
    ),
    'working_time': _('Would this working arrangement suit you: %(requirement)s?'),
    'work_condition': _(
        'The offer mentions this working condition: %(requirement)s. Would it suit you?'
    ),
    'mobility': _(
        'Can you get to the workplace under these conditions: %(requirement)s?'
    ),
    'contract': _('Would this type of contract suit you: %(requirement)s?'),
    'salary': _(
        'Does the pay stated in the offer meet your expectations: %(requirement)s?'
    ),
    'permit': _('Do you have the permit stated in the offer: %(requirement)s?'),
    'skill': _('Can you use this skill on the job: %(requirement)s?'),
    'language': _(
        'Can you work in the language and at the level stated: %(requirement)s?'
    ),
}

DEFAULT_QUESTION_TEMPLATE = _('%(condition)s: %(requirement)s. Would that suit you?')


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, cls=DjangoJSONEncoder).encode()
    ).hexdigest()


def candidate_reviews(user):
    if not user.is_authenticated or not user.is_active or user.kind != 'candidate':
        return CandidateOfferReview.objects.none()
    return CandidateOfferReview.objects.filter(
        match__candidate__in=access.candidates().filter(user=user),
    ).filter(
        Q(match__offer__in=access.offers())
        | Q(match__decision='retained', match__offer__in=access.matchable_offers())
    )


@transaction.atomic
def request_offer_review(user, match_id):
    if not access.can_change_match(user):
        raise PermissionDenied
    match = CandidateOfferMatch.objects.select_for_update().get(
        pk=match_id, candidate__in=access.candidates(), offer__in=access.offers()
    )
    review, _ = CandidateOfferReview.objects.get_or_create(
        match=match, defaults={'requested_by_adviser': user}
    )
    return review


def short_question(row):
    if (
        row['kind'] == 'schedule'
        and row['askable']
        and row['presented']['expected']['slots'] == ['saturday:morning']
        and row['presented']['expected']['mandatory']
    ):
        return _('The job requires Saturday mornings. Can you work those hours?')
    return ''


def question_text(row):
    if row['kind'] == 'availability':
        latest = row['presented']['expected'].get('latest_start')
        if latest:
            return str(
                _(
                    'The job would need to start by %(date)s at the latest. Would you be available by then?'
                )
                % {'date': readable_date(latest)}
            )
    short = short_question(row)
    if short:
        return str(short)
    if row['kind'] == 'occupation' and row.get('common_skills'):
        return str(
            _(
                'You mentioned these skills: %(skills)s. This job could use them. Would you like to consider it: %(job)s?'
            )
            % {'skills': ', '.join(row['common_skills']), 'job': row['expected']}
        )
    template = QUESTION_TEMPLATES.get(row['kind'], DEFAULT_QUESTION_TEMPLATE)
    return str(template % {'condition': row['label'], 'requirement': row['expected']})


def questions(review):
    match = review.match
    match.offer.refresh_from_db()
    match.candidate.refresh_from_db()
    data, _ = inputs(match)
    candidate, offer, requirements = (
        data['candidate'],
        data['offer'],
        data['requirements'],
    )
    result = evaluate(
        candidate, offer, requirements, data['facts'], today=timezone.localdate()
    )
    context = {key: offer.get(key, '') for key in ('title', 'companyName', 'city')}
    # Keep the former empty workspace key so existing company-less consents stay valid.
    context['company_id'] = ''
    rows = []
    fields = {
        'occupation': ('project_mode', 'occupation_references', 'desired_occupations'),
        'skill': ('acquired_skills', 'learning_activities', 'occupation_skills'),
        'skills': ('acquired_skills', 'learning_activities', 'occupation_skills'),
        'language': ('language_skills',),
        'languages': ('language_skills',),
        'mobility': (
            'desired_countries',
            'desired_locations',
            'mobility',
            'commute_time',
            'transport_modes',
            'transport_details',
        ),
        'availability': ('availability', 'available_from'),
        'schedule': (
            'schedule_preference',
            'schedule_strict',
            *('schedule_' + day for day in DAYS),
        ),
        'permit': ('licences_held', 'licence_details'),
        'permits': ('licences_held', 'licence_details'),
        'work_condition': ('working_conditions', 'condition_details'),
        'work_conditions': ('working_conditions', 'condition_details'),
        'contract': ('contract_types', 'contract_details'),
        'salary': (
            'salary_preference',
            'salary_amount',
            'salary_currency',
            'salary_period',
            'salary_basis',
        ),
    }
    clar = offer.get('clarifications') or {}
    evidence = []
    for item in result['rows']:
        if item['key'] == 'schedule' and requirements.get('schedule'):
            # Each required slot can be confirmed or reserved independently.
            evidence.extend(
                {**item, 'reference': slot} for slot in requirements['schedule']
            )
        else:
            evidence.append(item)
    for row in evidence:
        if row['state'] == 'not_applicable':
            continue
        key, ref = row['key'], row['reference']
        expected = row['expected'] or ref
        if key == 'occupation':
            expected = ref or offer.get('title', '')
        elif key == 'skill':
            expected = ref
        elif key == 'language':
            expected = {'code': ref, 'level': row['expected']}
        elif key == 'mobility':
            expected = {
                'country': requirements.get('country', ''),
                'city': offer.get('city', ''),
                'commute': clar.get('commute', ''),
                'relocation': offer.get('relocation', ''),
            }
        elif key == 'availability':
            expected = {
                'latest_start': requirements.get('latest_start', ''),
                'mandatory': requirements.get('start_mandatory', False),
                'text': clar.get('startDate', ''),
            }
        elif key == 'schedule':
            expected = {
                'slots': [ref] if ref else [],
                'mandatory': requirements.get('schedule_mandatory', False),
                'text': clar.get('hours', ''),
            }
        elif key == 'contract':
            expected = offer.get('contractType', '')
        elif key == 'salary':
            expected = {
                'structured': requirements.get('salary', {}),
                'text': clar.get('salary', ''),
            }
        elif key == 'permit' and ref == 'other':
            expected = (offer.get('requirements') or {}).get('permitOther', '')
        elif key in ('permits', 'work_conditions', 'skills', 'languages'):
            expected = ''
        # Missing employer data never causes a question to the candidate.
        askable = bool(expected)
        if isinstance(expected, dict):
            askable = any(
                value for name, value in expected.items() if name != 'mandatory'
            )
        if row['reason'] == 'alternative_occupations':
            askable = False
        presented = {
            'version': VERSION,
            'context': context,
            'key': key,
            'reference': ref,
            'expected': expected,
            'declared': {name: candidate.get(name) for name in fields[key]},
            'askable': askable,
        }
        if key == 'occupation':
            presented['common_skills'] = [
                item['reference']
                for item in result['rows']
                if item['key'] == 'skill' and item['state'] == 'match'
            ]
        if key == 'schedule' and ref:
            day = ref.split(':')[0]
            presented['declared'] = {
                name: candidate.get(name)
                for name in (
                    'schedule_preference',
                    'schedule_strict',
                    'schedule_' + day,
                )
            }
        if key == 'skill':
            from .engine import skill_set

            presented['declared'] = {
                'acquired_skills': (
                    [ref]
                    if ref
                    in set(candidate.get('acquired_skills', []))
                    | skill_set(candidate.get('occupation_skills'))
                    else []
                ),
                'learning_activities': (
                    [ref] if ref in candidate.get('learning_activities', []) else []
                ),
            }
        # Relative availability has no field-specific reference date: reconfirm on a new day.
        if key == 'availability':
            presented['as_of'] = timezone.localdate().isoformat()
        presented = json.loads(json.dumps(presented, cls=DjangoJSONEncoder))
        rows.append(
            {
                'key': key + ':' + ref,
                'kind': key,
                'reference': ref,
                'presented': presented,
                'fingerprint': digest(presented),
                'askable': askable,
                'priority': (
                    0
                    if row['blocking'] or row['state'] == 'mismatch'
                    else (1 if row['state'] == 'unknown' else 2)
                ),
            }
        )
    # Working hours are meaningful even though the experimental score ignores them.
    presented = {
        'version': VERSION,
        'context': context,
        'key': 'working_time',
        'reference': '',
        'expected': clar.get('hours', ''),
        'declared': {'working_time': candidate.get('working_time', [])},
        'askable': bool(clar.get('hours')),
    }
    rows.append(
        dict(
            key='working_time:',
            kind='working_time',
            reference='',
            presented=presented,
            fingerprint=digest(presented),
            askable=presented['askable'],
        )
    )
    presented = {
        'version': VERSION,
        'context': context,
        'key': 'employer',
        'reference': '',
        'expected': offer.get('companyName', '').strip(),
        'declared': {},
        'askable': bool(offer.get('companyName', '').strip()),
    }
    rows.append(
        dict(
            key='employer:',
            kind='employer',
            reference='',
            presented=presented,
            fingerprint=digest(presented),
            askable=presented['askable'],
        )
    )
    rows.sort(key=question_order)
    return rows


def question_order(row):
    if row['kind'] == 'occupation':
        return (0, 0)
    if row['kind'] == 'employer':
        return (3, 0)
    return (
        (
            1
            if row['kind']
            in {'schedule', 'availability', 'working_time', 'work_condition'}
            else 2
        ),
        row.get('priority', 1),
    )


def needs_answer(row):
    return row['askable'] and (
        not row['answer']
        or (
            row['kind'] in {'occupation', 'employer'}
            and row['answer'].value == 'clarify'
        )
    )


def review_state(review):
    rows = questions(review)
    latest = {}
    for answer in review.answers.order_by('-pk'):
        latest.setdefault(answer.question_key, answer)
    for row in rows:
        answer = latest.get(row['key'])
        row['answer'] = (
            answer if answer and answer.fingerprint == row['fingerprint'] else None
        )
        row['stale'] = bool(answer and not row['answer']) or (
            not answer and any(key.startswith(row['kind'] + ':') for key in latest)
        )
    fingerprint = digest(
        {
            'version': VERSION,
            'offer': review.match.offer.data,
            'profile': {
                field.name: getattr(review.match.candidate, field.name)
                for field in review.match.candidate._meta.fields
                if field.name not in ('user', 'id')
            },
            # Same compatibility key as before retirement; no model lookup remains.
            'company': '',
            'questions': [
                (
                    row['key'],
                    row['fingerprint'],
                    row['answer'].pk if row['answer'] else None,
                )
                for row in rows
            ],
        }
    )
    profile_sharing = review.profile_sharings.order_by('-pk').first()
    current_profile_sharing = (
        profile_sharing
        if profile_sharing and profile_sharing.fingerprint == fingerprint
        else None
    )
    declined = next(
        (
            row
            for row in rows
            if row['kind'] in {'occupation', 'employer'}
            and row['answer']
            and row['answer'].value == 'no'
        ),
        None,
    )
    scope_pending = (
        None
        if declined
        else next(
            (
                row
                for row in rows
                if row.get('priority') == 2
                and row['kind'] not in {'occupation', 'employer'}
                and row['answer']
                and row['answer'].value == 'no'
                and row['answer'].dialogue.get('scope') == ''
            ),
            None,
        )
    )
    return dict(
        scope_pending=scope_pending,
        declined=declined,
        rows=rows,
        fingerprint=fingerprint,
        agreement=current_profile_sharing,
        pending=scope_pending or next((row for row in rows if needs_answer(row)), None),
        unresolved=any(
            not row['askable'] or not row['answer'] or row['answer'].value != 'yes'
            for row in rows
        ),
    )


def candidate_progress(review):
    """Current candidate action, independent from email delivery or page visits."""
    state = review_state(review)
    if state['declined']:
        return 'declined', state
    if state['agreement']:
        return 'completed', state
    if review.answers.exists() or review.profile_sharings.exists():
        return 'in_progress', state
    return 'not_started', state


def locked_review(user, pk):
    # Serialize candidate answers and agreements on the pair as well as the review.
    review = candidate_reviews(user).get(pk=pk)
    CandidateOfferMatch.objects.select_for_update().get(pk=review.match_id)
    review = (
        candidate_reviews(user)
        .select_for_update(of=('self',))
        .select_related('match__candidate', 'match__offer')
        .get(pk=pk)
    )
    # Lock the same business objects as profile/offer changes before checking fingerprints.
    from eures_beta.candidates.models import CandidateProfile
    from eures_beta.employers.models import JobOffer

    CandidateProfile.objects.select_for_update().get(pk=review.match.candidate_id)
    JobOffer.objects.select_for_update().get(pk=review.match.offer_id)
    return (
        candidate_reviews(user)
        .select_related('match__candidate', 'match__offer')
        .get(pk=pk)
    )


@transaction.atomic
def answer(user, pk, key, fingerprint, value, detail='', previous=0, *, dialogue=None):
    review = locked_review(user, pk)
    row = next(
        (row for row in questions(review) if row['key'] == key and row['askable']),
        None,
    )
    if (
        review_state(review)['declined']
        and row
        and row['kind'] not in {'occupation', 'employer'}
    ):
        raise ValueError('This offer was declined')
    if not row or row['fingerprint'] != fingerprint:
        raise StaleEvaluation
    if (
        value not in VALUES
        or not isinstance(detail, str)
        or len(detail) > 2000
        or (value in ('conditional', 'changed', 'clarify') and not detail.strip())
    ):
        raise ValueError('Invalid confirmation')
    latest = review.answers.filter(question_key=key).order_by('-pk').first()
    if (
        latest
        and latest.fingerprint == fingerprint
        and latest.value == value
        and latest.detail == detail.strip()
    ):
        return latest
    if (latest.pk if latest else 0) != previous:
        raise StaleEvaluation
    event = CandidateOfferReviewAnswer.objects.create(
        review=review,
        question_key=key,
        fingerprint=fingerprint,
        presented=row['presented'],
        value=value,
        detail=detail.strip(),
        dialogue=(
            dialogue
            if dialogue is not None
            else {'scope': 'profile' if value == 'changed' else 'offer'}
        ),
    )
    from . import review_workflow

    review_workflow.check_repeated_refusal(event)
    review_workflow.sync(review, user)
    return event


@transaction.atomic
def confirm_scope(user, pk, key, fingerprint, previous, scope):
    review = locked_review(user, pk)
    state = review_state(review)
    row = state['scope_pending']
    if (
        not row
        or row['key'] != key
        or row['fingerprint'] != fingerprint
        or row['answer'].pk != previous
        or scope not in {'offer', 'profile'}
    ):
        raise StaleEvaluation
    source = row['answer']
    event = CandidateOfferReviewAnswer.objects.create(
        review=review,
        question_key=key,
        fingerprint=fingerprint,
        presented=row['presented'],
        value=source.value,
        detail=source.detail,
        dialogue={**source.dialogue, 'scope': scope},
    )
    from . import review_workflow
    from eures_beta.candidates.models import CandidateProfileReviewSuggestion

    identity = review_workflow.condition_identity(row['presented'])
    CandidateProfileReviewSuggestion.objects.filter(
        candidate=review.match.candidate,
        condition_hash=digest(identity),
        profile_updated_at=review.match.candidate.updated_at,
        resolution='',
    ).update(
        resolution='keep' if scope == 'offer' else 'review', resolved_at=timezone.now()
    )
    review_workflow.sync(review, user)
    return event


@transaction.atomic
def agree(user, pk, fingerprint, agreed, previous=0):
    review = locked_review(user, pk)
    state = review_state(review)
    if fingerprint != state['fingerprint']:
        raise StaleEvaluation
    employer = next(row for row in state['rows'] if row['kind'] == 'employer')
    if (
        state['pending']
        or type(agreed) is not bool
        or (
            agreed
            and (
                state['declined']
                or not employer['answer']
                or employer['answer'].value not in {'yes', 'conditional'}
            )
        )
    ):
        raise ValueError('Review the conditions first')
    latest = review.profile_sharings.order_by('-pk').first()
    if latest and latest.fingerprint == fingerprint and latest.agreed == agreed:
        return latest
    if (latest.pk if latest else 0) != previous:
        raise StaleEvaluation
    event = CandidateProfileSharing.objects.create(
        review=review, fingerprint=fingerprint, agreed=agreed
    )
    from . import review_workflow

    review_workflow.sync(review, user)
    return event
