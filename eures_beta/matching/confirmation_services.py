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

VERSION = 'offer-confirmation-v1'
VALUES = {'yes', 'conditional', 'no', 'changed', 'clarify'}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, cls=DjangoJSONEncoder).encode()
    ).hexdigest()


def candidate_requests(user):
    if (
        not access.enabled()
        or not user.is_authenticated
        or not user.is_active
        or user.kind != 'candidate'
    ):
        return CandidateOfferReview.objects.none()
    return CandidateOfferReview.objects.filter(
        pair__candidate__in=access.candidates().filter(user=user),
    ).filter(
        Q(pair__offer__in=access.offers())
        | Q(pair__decision='retained', pair__offer__in=access.matchable_offers())
    )


@transaction.atomic
def request_confirmation(user, pair_id):
    if not access.can_change_pair(user):
        raise PermissionDenied
    pair = CandidateOfferMatch.objects.select_for_update().get(
        pk=pair_id, candidate__in=access.candidates(), offer__in=access.offers()
    )
    request, _ = CandidateOfferReview.objects.get_or_create(
        pair=pair, defaults={'requested_by': user}
    )
    return request


def short_question(row):
    if (
        row['kind'] == 'schedule'
        and row['askable']
        and row['presented']['expected']['slots'] == ['saturday:morning']
        and row['presented']['expected']['mandatory']
    ):
        return _('The job requires Saturday mornings. Can you work those hours?')
    return ''


def questions(request):
    pair = request.pair
    pair.offer.refresh_from_db()
    pair.candidate.refresh_from_db()
    data, _ = inputs(pair)
    candidate, offer, requirements = (
        data['candidate'],
        data['offer'],
        data['requirements'],
    )
    result = evaluate(
        candidate, offer, requirements, data['facts'], today=timezone.localdate()
    )
    context = {key: offer.get(key, '') for key in ('title', 'companyName', 'city')}
    # The identity of the recipient is bound too, without copying contact details.
    context['company_id'] = str(pair.offer.company_id or '')
    rows = []
    fields = {
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
        if key == 'skill':
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
    rows.sort(key=lambda row: row.get('priority', 1))
    return rows


def review(request):
    rows = questions(request)
    latest = {}
    for answer in request.answers.order_by('-pk'):
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
            'offer': request.pair.offer.data,
            'profile': {
                field.name: getattr(request.pair.candidate, field.name)
                for field in request.pair.candidate._meta.fields
                if field.name not in ('user', 'id')
            },
            'company': str(request.pair.offer.company_id or ''),
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
    agreement = request.agreements.order_by('-pk').first()
    current_agreement = (
        agreement if agreement and agreement.fingerprint == fingerprint else None
    )
    return dict(
        rows=rows,
        fingerprint=fingerprint,
        agreement=current_agreement,
        pending=next(
            (row for row in rows if row['askable'] and not row['answer']), None
        ),
        unresolved=any(
            not row['askable'] or not row['answer'] or row['answer'].value != 'yes'
            for row in rows
        ),
    )


def locked_request(user, pk):
    # Serialize candidate answers and agreements on the pair as well as the request.
    request = candidate_requests(user).get(pk=pk)
    CandidateOfferMatch.objects.select_for_update().get(pk=request.pair_id)
    request = (
        candidate_requests(user)
        .select_for_update(of=('self',))
        .select_related('pair__candidate', 'pair__offer')
        .get(pk=pk)
    )
    # Lock the same business objects as profile/offer changes before checking fingerprints.
    from eures_beta.candidates.models import CandidateProfile
    from eures_beta.employers.models import JobOffer

    CandidateProfile.objects.select_for_update().get(pk=request.pair.candidate_id)
    JobOffer.objects.select_for_update().get(pk=request.pair.offer_id)
    return (
        candidate_requests(user)
        .select_related('pair__candidate', 'pair__offer')
        .get(pk=pk)
    )


@transaction.atomic
def answer(user, pk, key, fingerprint, value, detail='', previous=0, *, dialogue=None):
    request = locked_request(user, pk)
    row = next(
        (row for row in questions(request) if row['key'] == key and row['askable']),
        None,
    )
    if not row or row['fingerprint'] != fingerprint:
        raise StaleEvaluation
    if (
        value not in VALUES
        or not isinstance(detail, str)
        or len(detail) > 2000
        or (value in ('conditional', 'changed', 'clarify') and not detail.strip())
    ):
        raise ValueError('Invalid confirmation')
    latest = request.answers.filter(question_key=key).order_by('-pk').first()
    if (
        latest
        and latest.fingerprint == fingerprint
        and latest.value == value
        and latest.detail == detail.strip()
    ):
        return latest
    if (latest.pk if latest else 0) != previous:
        raise StaleEvaluation
    return CandidateOfferReviewAnswer.objects.create(
        request=request,
        actor=user,
        question_key=key,
        fingerprint=fingerprint,
        presented=row['presented'],
        value=value,
        detail=detail.strip(),
        dialogue=dialogue or {},
    )


@transaction.atomic
def agree(user, pk, fingerprint, agreed, previous=0):
    request = locked_request(user, pk)
    state = review(request)
    if fingerprint != state['fingerprint']:
        raise StaleEvaluation
    if state['pending'] or type(agreed) is not bool:
        raise ValueError('Review the conditions first')
    latest = request.agreements.order_by('-pk').first()
    if latest and latest.fingerprint == fingerprint and latest.agreed == agreed:
        return latest
    if (latest.pk if latest else 0) != previous:
        raise StaleEvaluation
    return CandidateProfileSharing.objects.create(
        request=request, actor=user, fingerprint=fingerprint, agreed=agreed
    )
