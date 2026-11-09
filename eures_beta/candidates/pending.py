"""Short-lived confirmation packages in Django's existing session table.

These dedicated rows never hold authentication or a browser session key.
The signed link only contains a random identifier and a single-use nonce.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone

PREFIX = 'cand_'
PAYLOAD = 'candidate_confirmation'


def session_key(identifier):
    return PREFIX + hashlib.sha256(str(identifier).encode()).hexdigest()[:35]


@dataclass
class Pending:
    pk: uuid.UUID
    nonce: uuid.UUID
    email: str
    language: str
    answers: dict
    created_at: datetime
    expires_at: datetime

    def delete(self):
        Session.objects.filter(session_key=session_key(self.pk)).delete()


def store(email, answers, language):
    now = timezone.now()
    pending = Pending(
        uuid.uuid4(),
        uuid.uuid4(),
        email,
        language,
        answers,
        now,
        now + timedelta(seconds=settings.CANDIDATE_REGISTRATION_MAX_AGE),
    )
    payload = {
        'id': str(pending.pk),
        'nonce': str(pending.nonce),
        'email': email,
        'language': language,
        'answers': answers,
        'created_at': now.isoformat(),
    }
    Session.objects.create(
        session_key=session_key(pending.pk),
        session_data=SessionStore().encode({PAYLOAD: payload}),
        expire_date=pending.expires_at,
    )
    return pending


def load(identifier, nonce, *, lock=False):
    query = Session.objects.select_for_update() if lock else Session.objects
    row = query.filter(
        session_key=session_key(identifier), expire_date__gt=timezone.now()
    ).first()
    data = row.get_decoded().get(PAYLOAD, {}) if row else {}
    if data.get('id') != str(identifier) or data.get('nonce') != str(nonce):
        return None
    return Pending(
        identifier,
        nonce,
        data['email'],
        data['language'],
        data['answers'],
        datetime.fromisoformat(data['created_at']),
        row.expire_date,
    )


def expired():
    return Session.objects.filter(
        session_key__startswith=PREFIX, expire_date__lte=timezone.now()
    )


def latest_for_email(email):
    # Private operator command only; no public lookup by address.
    requests = []
    for row in Session.objects.filter(
        session_key__startswith=PREFIX, expire_date__gt=timezone.now()
    ).iterator():
        data = row.get_decoded().get(PAYLOAD, {})
        if data.get('email', '').lower() == email.strip().lower():
            item = load(uuid.UUID(data['id']), uuid.UUID(data['nonce']))
            if item:
                requests.append(item)
    return max(requests, key=lambda item: item.created_at, default=None)
