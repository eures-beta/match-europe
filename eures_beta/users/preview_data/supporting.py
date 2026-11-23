"""Small supporting records, always labelled fictional and without external I/O."""

from datetime import timedelta
import hashlib
import uuid

from django.conf import settings
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile, CandidatePushSubscription
from eures_beta.candidates.pending import PAYLOAD, session_key
from eures_beta.employers.models import EmployerProfile, JobOffer
from eures_beta.invitations.models import Invitation
from eures_beta.skills.models import OccupationSkillSuggestion
from eures_beta.skills.skills_pilot import catalogue
from eures_beta.users.models import LoginRateLimit


def seed_supporting_data(users):
    now = timezone.now()
    for key, coverage, delay in (
        ('employer', 'all', 'under_week'),
        ('matching-employer', 'selected', 'one_two_weeks'),
    ):
        EmployerProfile.objects.get_or_create(
            user=users[key],
            defaults={'response_coverage': coverage, 'response_time': delay},
        )
    for key, kind, accepted, expired in (
        ('waiting', 'employer', False, False),
        ('expired', 'candidate', False, True),
        ('accepted', 'employer', True, False),
    ):
        email = (
            users['matching-employer'].email
            if accepted
            else f'invitation-{key}@preview-dataset.invalid'
        )
        Invitation.objects.get_or_create(
            email=email,
            defaults={
                'sender_adviser': users['adviser'],
                'recipient_kind': kind,
                'first_name': 'Invitation fictive',
                'last_name': key,
                'created_at': now - timedelta(days=3),
                'email_sent_at': now - timedelta(days=3),
                'expires_at': now + timedelta(days=-1 if expired else 7),
                'accepted_at': now - timedelta(days=2) if accepted else None,
                'recipient': users['matching-employer'] if accepted else None,
            },
        )
    cards, _ = catalogue()
    for key in ('nettoyage', 'nettoyage-locaux'):
        card = cards[key]
        OccupationSkillSuggestion.objects.get_or_create(
            occupation_uri=card['occupation']['uri'],
            source_version='preview-official-fixture-v1',
            method='fixture:official-relations',
            defaults={
                'status': 'ready',
                'skill_uris': [item['skillUri'] for item in card['keySkills'][:3]],
            },
        )
    # These reserved invalid endpoints cannot pass the real Push host allowlist.
    # Use non-selector profiles so the two selectable candidates can opt in normally.
    for key in ('date', 'schedule'):
        profile = CandidateProfile.objects.get(
            user__email=key + '@matching-trial.invalid'
        )
        CandidatePushSubscription.objects.get_or_create(
            candidate=profile,
            defaults={
                'endpoint': f'https://push.preview-dataset.invalid/{key}',
                'keys': {
                    'p256dh': 'fictional-not-a-browser-key',
                    'auth': 'fictional-not-a-browser-secret',
                },
            },
        )
    for key in ('draft-a', 'draft-b'):
        identifier = uuid.uuid5(
            uuid.NAMESPACE_URL, 'match-europe.preview-dataset.' + key
        )
        Session.objects.get_or_create(
            session_key=session_key(identifier),
            defaults={
                'session_data': SessionStore().encode(
                    {
                        PAYLOAD: {
                            'id': str(identifier),
                            'nonce': str(uuid.uuid4()),
                            'email': key + '@preview-dataset.invalid',
                            'language': 'fr',
                            'answers': {},
                            'created_at': now.isoformat(),
                        }
                    }
                ),
                'expire_date': now
                + timedelta(seconds=settings.CANDIDATE_REGISTRATION_MAX_AGE),
            },
        )
        LoginRateLimit.objects.get_or_create(
            key=hashlib.sha256(('preview-dataset.' + key).encode()).hexdigest()[:40],
            defaults={'attempts': 1, 'expires': now - timedelta(days=1)},
        )
    content_type = ContentType.objects.get_for_model(JobOffer)
    for offer in JobOffer.objects.filter(session_key='preview-dataset-v1').order_by(
        'pk'
    )[:2]:
        LogEntry.objects.get_or_create(
            user=users['admin'],
            content_type=content_type,
            object_id=str(offer.pk),
            action_flag=ADDITION,
            change_message='[Fictif] Initialisation du jeu de recette.',
            defaults={'object_repr': offer.data['title']},
        )
