import hashlib
import json
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from . import engine, validation
from .access import candidates, matchable_offers
from .models import CandidateOfferMatch, MatchEvaluation, MatchDecision


class StaleEvaluation(ValueError):
    pass


def inputs(match, *, lock=False, offer_revision=None):
    # Re-read eligible objects: disablement/revocation also invalidates matching access.
    candidate_query, offer_query = candidates(), matchable_offers()
    if offer_revision is not None:
        offer_query = offer_query.filter(revision=offer_revision)
    if lock:
        candidate_query = candidate_query.select_for_update(of=('self',))
        offer_query = offer_query.select_for_update(of=('self',))
    candidate = candidate_query.get(pk=match.candidate_id)
    offer = offer_query.get(pk=match.offer_id)
    excluded = {
        'id',
        'user',
        'display_name',
        'language',
        'notice_read_at',
        'notice_version',
        'email_verified_at',
        'created_at',
    }
    profile = {
        field.name: getattr(candidate, field.name)
        for field in candidate._meta.fields
        if field.name not in excluded
    }
    requirements = offer.structured_requirements
    validation.requirements(requirements)
    validation.candidate_facts(match.candidate_facts)
    data = dict(
        candidate=profile,
        offer=offer.data,
        requirements=requirements,
        facts=match.candidate_facts,
        offer_revision=offer.revision,
        version=engine.VERSION,
        weights=engine.WEIGHTS,
        date=timezone.localdate().isoformat(),
    )
    fingerprint = hashlib.sha256(
        json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True).encode()
    ).hexdigest()
    return data, fingerprint


@transaction.atomic
def calculate(candidate, offer, *, offer_revision=None):
    match, _ = CandidateOfferMatch.objects.get_or_create(
        candidate=candidate, offer=offer
    )
    match = CandidateOfferMatch.objects.select_for_update().get(pk=match.pk)
    data, fingerprint = inputs(match, lock=True, offer_revision=offer_revision)
    if offer_revision is not None:
        latest = match.evaluations.order_by('-id').first()
        if latest and latest.fingerprint == fingerprint:
            return latest
    result = engine.evaluate(
        data['candidate'],
        data['offer'],
        data['requirements'],
        data['facts'],
        today=timezone.localdate(),
    )
    evaluation = MatchEvaluation.objects.create(
        match=match,
        fingerprint=fingerprint,
        rules_version=engine.VERSION,
        result=result,
    )
    # Human decisions are never overwritten by a calculation.
    return evaluation


@transaction.atomic
def decide(match_id, evaluation_id, value, *, actor='local_operator'):
    if value not in ('retained', 'refused'):
        raise ValueError('Invalid matching decision')
    match = CandidateOfferMatch.objects.select_for_update().get(pk=match_id)
    evaluation = match.evaluations.order_by('-id').first()
    _, current = inputs(match, lock=True)
    if (
        not evaluation
        or evaluation.pk != evaluation_id
        or current != evaluation.fingerprint
    ):
        raise StaleEvaluation('Recalculate before deciding')
    if value == 'retained' and (
        evaluation.result['blocked'] or not evaluation.result['matched']
    ):
        raise ValueError(
            'Unresolved blocking condition or no established correspondence'
        )
    previous = match.decisions.order_by('-id').first()
    if (
        not previous
        or previous.evaluation_id != evaluation.pk
        or previous.value != value
    ):
        match.decision = value
        match.save(update_fields=['decision'])
        MatchDecision.objects.create(
            match=match, evaluation=evaluation, value=value, actor=actor
        )
    return match


def calculate_for_saved_offer(offer_id, revision):
    offer = matchable_offers().filter(pk=offer_id, revision=revision).first()
    if offer is None:
        return
    for candidate in candidates().order_by('pk').iterator():
        try:
            calculate(candidate, offer, offer_revision=revision)
        except ObjectDoesNotExist:
            # The offer or candidate can become ineligible after scheduling.
            continue


def schedule_offer_matching(offer):
    offer_id, revision = offer.pk, offer.revision
    transaction.on_commit(
        lambda: calculate_for_saved_offer(offer_id, revision),
        robust=True,
    )
