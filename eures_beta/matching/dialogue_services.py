"""Local, deterministic stand-in for an Albert dialogue. Never calls a model.

Only a deliberately small, reviewed multilingual corpus is recognised. Anything
else requires an explicit clarification or the existing manual journey.
"""

import unicodedata

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.translation import gettext as _

from . import access, confirmation_services as confirmations
from .services import StaleEvaluation

SALT = 'matching.simulated-dialogue.v1'
MAX_AGE = 15 * 60


def enabled():
    return settings.CONFIRMATION_DIALOGUE_SIMULATED and access.enabled()


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


def make_proposal(user, pk, key, fingerprint, context, previous, text, scope=''):
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
    result = interpret(text, row, scope)
    if result is None:
        return None
    if result['patch'] and not obj.pair.candidate.schedule_saturday:
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
