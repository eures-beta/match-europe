import json
import secrets
import time
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from . import continuous, albert_skills
from .skills_pilot import choices


@never_cache
@require_POST
def suggestions(request):
    if not continuous.trial_request(request):
        raise Http404
    if len(request.body) > 4000:
        return JsonResponse({'error': 'invalid_data'}, status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError()
        uri, role, language = (
            payload['occupation'],
            payload['role'],
            payload['language'],
        )
        if not isinstance(uri, str) or language not in ('fr', 'en', 'de'):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'error': 'invalid_data'}, status=400)
    if role == 'employer':
        from eures_beta.employers.employer_ownership import identity

        if not identity(request):
            return JsonResponse({'error': 'forbidden'}, status=403)
    elif role == 'candidate':
        from eures_beta.candidates.journey import KEY, TTL

        draft = request.session.get(KEY, {})
        token = payload.get('token', '')
        if (
            not request.user.is_authenticated
            or not request.user.is_active
            or request.user.kind != 'candidate'
            or draft.get('owner_id') != request.user.pk
            or not draft
            or time.time() - draft.get('touched_at', 0) > TTL
            or not isinstance(token, str)
            or not secrets.compare_digest(token, draft.get('token', ''))
        ):
            return JsonResponse({'error': 'expired'}, status=403)
    else:
        return JsonResponse({'error': 'invalid_data'}, status=400)
    try:
        card = continuous.reference_card(uri, generate=True)
    except (albert_skills.SuggestionUnavailable, ValueError, KeyError):
        return JsonResponse({'error': 'unavailable'}, status=503)
    return JsonResponse(
        {
            'occupation': uri,
            'label': card['occupation']['labels'][language],
            'skills': choices(card, 'keySkills', language),
            'behaviours': choices(card, 'behaviours', language),
            'simulated': bool(card.get('simulated')),
            'generated': bool(card.get('generated')),
        }
    )
