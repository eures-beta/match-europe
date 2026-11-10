import hashlib
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from . import engine, validation
from .access import candidates, offers, enabled
from .models import MatchPair, MatchEvaluation, MatchDecision, OfferRequirements


class StaleEvaluation(ValueError):
    pass


def inputs(pair, *, lock=False):
    # Re-read eligible objects: disablement/revocation also invalidates local access.
    candidate_query, offer_query = candidates(), offers()
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
    requirements = (
        OfferRequirements.objects.filter(offer=offer)
        .values_list('data', flat=True)
        .first()
        or {}
    )
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
def calculate(candidate, offer):
    if not enabled():
        raise ValueError('Local matching is disabled')
    pair, _ = MatchPair.objects.get_or_create(candidate=candidate, offer=offer)
    pair = MatchPair.objects.select_for_update().get(pk=pair.pk)
    data, fingerprint = inputs(pair, lock=True)
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
        raise ValueError('Invalid local decision')
    pair = MatchPair.objects.select_for_update().get(pk=pair_id)
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
