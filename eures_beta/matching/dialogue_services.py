"""Local, deterministic stand-in for an Albert dialogue. Never calls a model.

Only a deliberately small, reviewed multilingual corpus is recognised. Anything
else requires an explicit clarification or the existing manual journey.
"""

import unicodedata
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils import timezone
from django.utils.crypto import salted_hmac
from eures_beta.users.models import LoginRateLimit

from . import access, confirmation_services as confirmations, dialogue_albert
from .services import StaleEvaluation

SALT = 'matching.simulated-dialogue.v1'
MAX_AGE = 15 * 60


def enabled():
    return (
        settings.CONFIRMATION_DIALOGUE_SIMULATED
        or (settings.CONFIRMATION_DIALOGUE_ENABLED and bool(settings.ALBERT_API_KEY))
    ) and access.enabled()


def live():
    return (
        settings.CONFIRMATION_DIALOGUE_ENABLED
        and not settings.CONFIRMATION_DIALOGUE_SIMULATED
    )


@transaction.atomic
def allow_call(user):
    now = timezone.now()
    key = salted_hmac('candidate-dialogue-quota', str(user.pk)).hexdigest()
    bucket, _ = LoginRateLimit.objects.select_for_update().get_or_create(
        key=key, defaults={'expires': now + timedelta(minutes=15)}
    )
    if bucket.expires <= now:
        bucket.attempts = 0
        bucket.expires = now + timedelta(minutes=15)
    if bucket.attempts >= 6:
        raise dialogue_albert.Unavailable
    bucket.attempts += 1
    bucket.save()


def normalise(text):
    return ' '.join(
        ''.join(
            c
            for c in unicodedata.normalize('NFKD', text.casefold())
            if not unicodedata.combining(c)
        )
        .strip(' .!')
        .split()
    )


def interpret(text, row, scope=''):
    """No guesswork outside the simulation corpus; scope is confirmed by the user."""
    text = text.strip()
    if not text or len(text) > 2000 or scope not in ('', 'offer', 'profile'):
        raise ValueError('Invalid reply')
    normal = normalise(text)
    yes = {'oui', 'yes', 'ja'}
    no = {'non', 'no', 'nein'}
    alternate = {'un samedi sur deux', 'every other saturday', 'jeden zweiten samstag'}
    unavailable = {
        'je ne suis plus disponible le samedi',
        'i am no longer available on saturdays',
        'ich bin samstags nicht mehr verfugbar',
    }
    patch = {}
    saturday = row['kind'] == 'schedule' and any(
        slot.startswith('saturday:') for slot in row['presented']['expected']['slots']
    )
    if normal in yes and scope != 'profile':
        value, scope = 'yes', 'offer'
    elif normal in no and scope != 'profile':
        value, scope = 'no', 'offer'
    elif saturday and normal in alternate and scope == 'offer':
        value = 'conditional'
    elif saturday and normal in unavailable and scope == 'profile':
        value = 'changed'
        patch = {'schedule_saturday': []}
    else:
        return None
    return {'value': value, 'scope': scope, 'patch': patch, 'text': text}


def question(obj, key):
    row = next(
        (r for r in confirmations.questions(obj) if r['key'] == key and r['askable']),
        None,
    )
    if row is None:
        raise StaleEvaluation
    return row


def make_proposal(
    user,
    pk,
    key,
    fingerprint,
    context,
    previous,
    text,
    scope='',
    language='fr',
    history_token='',
):
    if not enabled():
        raise PermissionDenied
    obj = confirmations.candidate_requests(user).get(pk=pk)
    row = question(obj, key)
    if (
        row['fingerprint'] != fingerprint
        or confirmations.review(obj)['fingerprint'] != context
    ):
        raise StaleEvaluation
    latest = obj.answers.filter(question_key=key).order_by('-pk').first()
    if (latest.pk if latest else 0) != previous:
        raise StaleEvaluation
    if live():
        history = []
        if history_token:
            prior = signing.loads(
                history_token, salt=SALT + '.history', max_age=MAX_AGE
            )
            if (
                prior['user'] != user.pk
                or prior['request'] != pk
                or prior['key'] != key
                or prior['context'] != context
            ):
                raise StaleEvaluation
            history = prior['history']
        if (
            language not in ('fr', 'en', 'de')
            or not isinstance(text, str)
            or not text.strip()
            or len(text) > 2000
            or len(history) >= 6
        ):
            raise dialogue_albert.Unavailable
        history = [*history, {'role': 'candidate', 'text': text.strip()}]
        source = '\n'.join(
            turn['text'] for turn in history if turn['role'] == 'candidate'
        )
        if len(source) > 2000:
            raise dialogue_albert.Unavailable
        allow_call(user)
        model = dialogue_albert.ask(row, source, scope, language, history)
        if model['outcome'] == 'clarify':
            history.append({'role': 'assistant', 'text': model['reply']})
            token = signing.dumps(
                dict(
                    user=user.pk, request=pk, key=key, context=context, history=history
                ),
                salt=SALT + '.history',
                compress=True,
            )
            return '', dict(
                clarification=model['reply'], history_token=token, turns=history[:-1]
            )
        result = dict(
            value=model['outcome'],
            scope=model['scope'],
            patch=model['changes'],
            text=source,
            reply=model['reply'],
            evidence=model['evidence'],
            provider='albert',
        )
    else:
        result = interpret(text, row, scope)
    if result is None:
        return None
    if not live() and result['patch'] and not obj.pair.candidate.schedule_saturday:
        # The request is still meaningful, but there is no profile change to propose.
        result['patch'] = {}
    payload = {
        'user': user.pk,
        'request': pk,
        'key': key,
        'fingerprint': fingerprint,
        'context': context,
        'previous': previous,
        **result,
        'provider': 'albert' if live() else 'simulation',
    }
    return signing.dumps(payload, salt=SALT, compress=True), result


@transaction.atomic
def accept(user, pk, token):
    if not enabled():
        raise PermissionDenied
    payload = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    if payload['user'] != user.pk or payload['request'] != pk:
        raise PermissionDenied
    obj = confirmations.locked_request(user, pk)
    if confirmations.review(obj)['fingerprint'] != payload['context']:
        raise StaleEvaluation
    row = question(obj, payload['key'])
    if payload.get('provider', 'simulation') != ('albert' if live() else 'simulation'):
        raise StaleEvaluation
    if live():
        model = dialogue_albert.validate(
            dict(
                reply=payload['reply'],
                outcome=payload['value'],
                scope=payload['scope'],
                changes=payload['patch'],
                evidence=payload['evidence'],
            ),
            row,
            payload['text'],
            payload['scope'],
        )
        result = dict(
            value=model['outcome'], patch=model['changes'], text=payload['text']
        )
    else:
        result = interpret(payload['text'], row, payload['scope'])
    if result is None:
        raise StaleEvaluation
    # Recompute the allowed change; a draft never supplies arbitrary profile fields.
    patch = result['patch'] if payload['patch'] else {}
    event = confirmations.answer(
        user,
        pk,
        row['key'],
        payload['fingerprint'],
        result['value'],
        result['text'],
        previous=payload['previous'],
    )
    return event, patch


def explanation(result):
    if result.get('provider') == 'albert':
        return result['reply']
    if result['scope'] == 'profile':
        return _(
            'You describe a general change. Confirm the proposed profile update separately from transmission permission.'
        )
    if result['value'] == 'conditional':
        return _(
            'You accept under conditions for this offer. Your general profile will stay unchanged.'
        )
    if result['value'] == 'no':
        return _(
            'You do not accept this condition for this offer. Your general profile will stay unchanged.'
        )
    return _(
        'This condition is still acceptable for this offer. Your general profile will stay unchanged.'
    )
