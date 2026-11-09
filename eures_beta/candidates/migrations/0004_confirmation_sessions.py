"""Move pending answers before dropping the redundant business model."""

import hashlib
from datetime import datetime

from django.contrib.sessions.backends.db import SessionStore
from django.db import migrations


def move_to_sessions(apps, schema_editor):
    Pending = apps.get_model('candidates', 'CandidateRegistration')
    Session = apps.get_model('sessions', 'Session')
    database = schema_editor.connection.alias
    for item in Pending.objects.using(database).iterator():
        payload = {
            'id': str(item.pk),
            'nonce': str(item.nonce),
            'email': item.email,
            'language': item.language,
            'answers': item.answers,
            'created_at': item.created_at.isoformat(),
        }
        key = 'cand_' + hashlib.sha256(str(item.pk).encode()).hexdigest()[:35]
        Session.objects.using(database).create(
            session_key=key,
            session_data=SessionStore().encode({'candidate_confirmation': payload}),
            expire_date=item.expires_at,
        )


def move_back(apps, schema_editor):
    Pending = apps.get_model('candidates', 'CandidateRegistration')
    Session = apps.get_model('sessions', 'Session')
    database = schema_editor.connection.alias
    rows = Session.objects.using(database).filter(session_key__startswith='cand_')
    for row in rows.iterator():
        data = SessionStore().decode(row.session_data).get('candidate_confirmation')
        if data is None:
            continue
        # The old schema cannot hold two independent drafts for the same email.
        # Abort the whole atomic rollback rather than silently discard one.
        if Pending.objects.using(database).filter(email__iexact=data['email']).exists():
            raise RuntimeError(
                'Cannot restore the old schema with duplicate email drafts.'
            )
        Pending.objects.using(database).create(
            id=data['id'],
            nonce=data['nonce'],
            email=data['email'],
            language=data['language'],
            answers=data['answers'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=row.expire_date,
        )
        row.delete(using=database)


class Migration(migrations.Migration):
    dependencies = [
        ('candidates', '0003_candidateprofile_email_verified_at_and_more'),
        ('sessions', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(move_to_sessions, move_back),
        migrations.DeleteModel(name='CandidateRegistration'),
    ]
