"""Linked fictional journeys; existing trials are never advanced or reset."""

from copy import deepcopy
from datetime import date, timedelta
import uuid

from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer
from eures_beta.users.models import AdviserAvailability
from eures_beta.matching import (
    offer_review_services as reviews,
    review_workflow,
    services,
)
from eures_beta.matching.models import (
    EmployerCandidateReview,
    CandidateOfferMatch,
    CandidateOfferReview,
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
    CandidateSupport,
    JobOfferSupport,
)
from .supporting import seed_supporting_data

NAMESPACE = 'match-europe.preview-dataset.v1.'
SCENARIOS = (
    ('refused', 'Rapprochement refusé', 'candidate-pwa', 'employer', 'refused'),
    ('closed', 'Revue close', 'candidate-pwa', 'employer', 'closed'),
    ('ready', 'Réponses à examiner', 'candidate-pwa', 'employer', 'ready'),
    (
        'claimed',
        'Dossier pris en charge',
        'candidate-pwa-replay',
        'employer',
        'claimed',
    ),
    ('clarify', 'Précision demandée', 'candidate-pwa', 'employer', 'clarify'),
    ('requested', 'Invitation à converser', 'candidate-pwa', 'employer', 'requested'),
    (
        'approved',
        'Conversation acceptée',
        'candidate-pwa-replay',
        'employer',
        'approved',
    ),
    ('open', 'Conversation ouverte', 'candidate-pwa', 'employer', 'open'),
    (
        'open-replay',
        'Échange en cours',
        'candidate-pwa-replay',
        'employer',
        'open',
    ),
    (
        'declined',
        'Invitation refusée',
        'candidate-pwa-replay',
        'employer',
        'declined',
    ),
    *[
        (
            f'preferences-{index}',
            f'Préférences à revoir {index}',
            'candidate-pwa',
            'employer',
            'preferences',
        )
        for index in range(1, 4)
    ],
)


def identifier(key):
    return uuid.uuid5(uuid.NAMESPACE_URL, NAMESPACE + key)


def seed_scenarios(users):
    adviser = users['adviser']
    AdviserAvailability.objects.get_or_create(
        adviser=adviser, day=date(2026, 11, 23), defaults={'present': True}
    )
    template = JobOffer.objects.get(
        employer=users['employer'], source_kind='matching', session_key='matching-trial'
    )
    for key, title, candidate_key, employer_key, phase in SCENARIOS:
        data = deepcopy(template.data)
        data.update(
            title=f'Offre fictive — {title}',
            description='Scénario fictif de recrutement pour explorer cet environnement de démonstration. Aucune candidature réelle.',
        )
        offer, _ = JobOffer.objects.get_or_create(
            pk=identifier(key),
            defaults={
                'employer': users[employer_key],
                'session_key': 'preview-dataset-v1',
                'source_kind': 'manual',
                'preparation_agreed_at': timezone.now(),
                'validated_at': timezone.now(),
                'data': data,
                'structured_requirements': deepcopy(template.structured_requirements),
            },
        )
        profile = CandidateProfile.objects.get(user=users[candidate_key])
        match, _ = CandidateOfferMatch.objects.get_or_create(
            candidate=profile, offer=offer
        )
        if (
            match.evaluations.exists()
            or match.decision != 'pending'
            or CandidateOfferReview.objects.filter(match=match).exists()
        ):
            # Even a partially explored fixture belongs to its tester after creation.
            continue
        evaluation = services.calculate(profile, offer)
        services.decide(
            match.pk,
            evaluation.pk,
            'refused' if phase == 'refused' else 'retained',
            by_adviser=adviser,
        )
        if phase == 'refused':
            continue
        review = reviews.request_offer_review(adviser, match.pk)
        for row in reviews.questions(review):
            if row['askable']:
                value = (
                    'no'
                    if phase == 'preferences' and row['kind'] in {'schedule', 'salary'}
                    else 'yes'
                )
                reviews.answer(
                    profile.user, review.pk, row['key'], row['fingerprint'], value
                )
        state = reviews.review_state(review)
        reviews.agree(
            profile.user,
            review.pk,
            state['fingerprint'],
            phase not in {'preferences', 'closed'},
        )
        review.refresh_from_db()
        if phase not in {'ready', 'preferences'}:
            handle(review, adviser, 'claim')
        if phase == 'clarify':
            handle(
                review,
                adviser,
                'clarify',
                message='[Fictif] Pouvez-vous préciser votre disponibilité le samedi ?',
            )
        elif phase == 'closed':
            handle(
                review,
                adviser,
                'refused',
                message='[Fictif] Cette proposition est close ; le profil reste disponible pour d’autres offres.',
            )
        elif phase in {'requested', 'approved', 'open', 'declined'}:
            handle(
                review,
                adviser,
                'validated',
                message='[Fictif] Les conditions ont été relues ensemble ; vous pouvez poursuivre cet échange.',
            )
            conversation(review, adviser, phase)
    for index, profile in enumerate(
        CandidateProfile.objects.filter(
            user__email__endswith='@matching-trial.invalid'
        ).order_by('pk')
    ):
        CandidateSupport.objects.get_or_create(
            candidate_profile=profile,
            defaults={
                'updated_by_adviser': adviser,
                'is_searching': True,
                'follow_up_on': timezone.localdate()
                + timedelta(days=(-1, 0, 3, 7, 14)[index % 5]),
            },
        )
    for index, offer in enumerate(
        JobOffer.objects.filter(employer=users['employer']).order_by('pk')
    ):
        JobOfferSupport.objects.get_or_create(
            job_offer=offer,
            defaults={
                'updated_by_adviser': adviser,
                'is_searching': index % 2 == 0,
                'follow_up_on': (
                    timezone.localdate() + timedelta(days=index)
                    if index % 2 == 0
                    else None
                ),
            },
        )
    # Add the new model to existing fixtures without advancing an explored request.
    review = CandidateOfferReview.objects.filter(
        match__offer_id=identifier('approved')
    ).first()
    if review:
        agreement = reviews.review_state(review)['agreement']
        if agreement and agreement.agreed:
            EmployerCandidateReview.objects.get_or_create(
                agreement=agreement,
                defaults={
                    'requested_by_adviser': adviser,
                    'employer': review.match.offer.employer,
                    'questions': [],
                },
            )
    seed_supporting_data(users)
    from .followups import seed_followups

    seed_followups(adviser, identifier)


def handle(review, adviser, action, *, message=''):
    state = reviews.review_state(review)
    review_workflow.handle(
        adviser,
        review.pk,
        action,
        review.workflow_version,
        state['fingerprint'],
        public_message=message,
    )
    review.refresh_from_db()


def conversation(review, adviser, phase):
    candidate, employer = review.match.candidate.user, review.match.offer.employer
    introduction = (
        '[Fictif] Bonjour, échangeons ici sur le poste et les prochaines étapes.'
    )
    thread = CandidateOfferConversation.objects.create(
        offer_review=review,
        adviser=adviser,
        candidate=candidate,
        employer=employer,
        state=phase,
        introduction=introduction,
        consent_at=None if phase == 'requested' else timezone.now(),
    )
    if phase == 'open':
        for author, body in (
            (adviser, introduction),
            (candidate, '[Fictif] Je suis disponible pour parler de cette offre.'),
            (
                employer,
                '[Fictif] Nous pouvons organiser un premier échange cette semaine.',
            ),
        ):
            CandidateOfferConversationMessage.objects.create(
                conversation=thread, author=author, body=body
            )
