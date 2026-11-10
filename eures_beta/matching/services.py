import hashlib
import json
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from . import engine, validation
from .access import candidates, enabled, matchable_offers
from .models import CandidateOfferMatch, MatchEvaluation, MatchDecision


class StaleEvaluation(ValueError):
    pass


def inputs(pair, *, lock=False, offer_revision=None):
    # Re-read eligible objects: disablement/revocation also invalidates matching access.
    candidate_query, offer_query = candidates(), matchable_offers()
    if offer_revision is not None:
        offer_query = offer_query.filter(revision=offer_revision)
    if lock:
        candidate_query = candidate_query.select_for_update(of=('self',))
        offer_query = offer_query.select_for_update(of=('self',))
    candidate = candidate_query.get(pk=pair.candidate_id)
    offer = offer_query.get(pk=pair.offer_id)
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
    validation.candidate_facts(pair.candidate_facts)
    data = dict(
        candidate=profile,
        offer=offer.data,
        requirements=requirements,
        facts=pair.candidate_facts,
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
    if not enabled():
        raise ValueError('Matching is disabled')
    pair, _ = CandidateOfferMatch.objects.get_or_create(candidate=candidate, offer=offer)
    pair = CandidateOfferMatch.objects.select_for_update().get(pk=pair.pk)
    data, fingerprint = inputs(pair, lock=True, offer_revision=offer_revision)
    if offer_revision is not None:
        latest = pair.evaluations.order_by('-id').first()
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
        pair=pair,
        fingerprint=fingerprint,
        rules_version=engine.VERSION,
        result=result,
    )
    # Human decisions are never overwritten by a calculation.
    return evaluation


@transaction.atomic
def decide(pair_id, evaluation_id, value):
    if not enabled() or value not in ('retained', 'refused'):
        raise ValueError('Invalid matching decision')
    pair = CandidateOfferMatch.objects.select_for_update().get(pk=pair_id)
    evaluation = pair.evaluations.order_by('-id').first()
    _, current = inputs(pair, lock=True)
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
    previous = pair.decisions.order_by('-id').first()
    if (
        not previous
        or previous.evaluation_id != evaluation.pk
        or previous.value != value
    ):
        pair.decision = value
        pair.save(update_fields=['decision'])
        MatchDecision.objects.create(pair=pair, evaluation=evaluation, value=value)
    return pair


def calculate_for_saved_offer(offer_id, revision):
    if not enabled():
        return
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
    if enabled():
        offer_id, revision = offer.pk, offer.revision
        transaction.on_commit(
            lambda: calculate_for_saved_offer(offer_id, revision),
            robust=True,
        )
