"""Private response practices: authenticated account only, versioned writes and CSRF."""

import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from eures_beta.users.models import User
from eures_beta.employers.employer_ownership import identity
from eures_beta.www.employer.access import employer_required
from eures_beta.employers.models import EmployerProfile
from eures_beta.www.employer.response_forms import ResponsePracticeForm


def serialize(practice):
    if practice is None:
        return {'revision': 0, 'response_coverage': '', 'response_time': ''}
    return {
        'revision': practice.revision,
        'response_coverage': practice.response_coverage,
        'response_time': practice.response_time,
    }


def page_context(person):
    practice = EmployerProfile.objects.filter(user=person).first() if person else None
    values = serialize(practice)
    return {
        'practice_form': ResponsePracticeForm(initial=values),
        'practice_values': values,
        'practice': practice,
    }


@never_cache
@employer_required
@require_http_methods(['GET', 'POST'])
def response_practice(request):
    person = identity(request)
    if request.method == 'GET':
        return JsonResponse(
            serialize(EmployerProfile.objects.filter(user=person).first())
        )
    try:
        if len(request.body) > 4096:
            raise ValueError
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or type(payload.get('revision')) is not int:
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_response_practice'}, status=400)
    form = ResponsePracticeForm(payload)
    if not form.is_valid():
        return JsonResponse({'error': 'invalid_response_practice'}, status=400)
    with transaction.atomic():
        # Lock the existing account even for the first answer, preventing concurrent creates.
        User.objects.select_for_update().get(pk=person.pk)
        practice = EmployerProfile.objects.filter(user=person).first()
        if payload['revision'] != (practice.revision if practice else 0):
            return JsonResponse({'error': 'conflict'}, status=409)
        if practice is None:
            practice = EmployerProfile(user=person)
        else:
            practice.revision += 1
        for name, value in form.cleaned_data.items():
            setattr(practice, name, value)
        practice.full_clean()
        practice.save()
    return JsonResponse(serialize(practice))
