from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from eures_beta.users.models import User
from eures_beta.candidates.models import CandidateProfile
from eures_beta.candidates.skill_choices import skill_groups
from eures_beta.employers.models import JobOffer
from eures_beta.employers.offer_ingestion import empty_data
from eures_beta.employers.employer_api import clean_data
from eures_beta.skills.skills_pilot import catalogue
from eures_beta.occupations.catalog import catalog
from eures_beta.matching.access import test_data_enabled
from eures_beta.matching.models import MatchPair, OfferRequirements
from eures_beta.matching.services import calculate, inputs


class Command(BaseCommand):
    help = 'Create fictional local matching scenarios; never overwrite profiles.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not test_data_enabled():
            raise CommandError(
                'Requires explicit fictional accounts in local/preview with no real email.'
            )
        cards, _ = catalogue()
        card = cards['nettoyage']
        uri = card['occupation']['uri']
        skills = [item['skillUri'] for item in card['keySkills'][:3]]
        behaviours = list(skill_groups()[0]['professional_behaviours'])[:3]
        employer, _ = User.objects.get_or_create(
            email='employer@matching-trial.invalid',
            defaults={'kind': 'employer', 'is_active': True},
        )
        if employer.kind != 'employer' or not employer.is_active:
            raise CommandError(
                'Reserved fictional account is unavailable; no account changed.'
            )
        title = 'Offre fictive — entretien'
        offer = JobOffer.objects.filter(
            email=employer.email, source_kind='matching'
        ).first()
        if offer is None:
            data = empty_data()
            data.update(
                title=title,
                companyName='Atelier fictif',
                city='Lieu fictif en France',
                contractType='PERMANENT_CONTRACT',
                occupation={
                    'version': catalog()['manifest']['version'],
                    'title': title,
                    'language': 'fr',
                    'uris': [uri],
                },
                occupationSkills={uri: {'skills': skills, 'behaviours': []}},
            )
            data['requirements'].update(
                permitRequired='yes', permits=['B'], workConditions=['weekend']
            )
            offer = JobOffer.objects.create(
                email=employer.email,
                session_key='matching-trial',
                created_by=employer,
                preparation_agreed_at=timezone.now(),
                validated_at=timezone.now(),
                source_kind='matching',
                data=clean_data(data),
            )
            OfferRequirements.objects.create(
                offer=offer,
                data={
                    'country': 'FR',
                    'languages': [{'code': 'fr', 'level': 'A2'}],
                    'latest_start': (
                        timezone.localdate() + timedelta(days=14)
                    ).isoformat(),
                    'start_mandatory': True,
                    'schedule': ['saturday:morning'],
                    'schedule_mandatory': True,
                    'mandatory_permits': ['B'],
                    'salary': {
                        'maximum': '22',
                        'currency': 'EUR',
                        'basis': 'gross',
                        'period': 'hour',
                    },
                },
            )
        scenarios = [
            ('compatible', 'Profil fictif A — correspondances', {}),
            (
                'unknown',
                'Profil fictif B — points à vérifier',
                {
                    'availability': 'discuss',
                    'available_from': None,
                    'schedule_preference': 'discuss',
                    'schedule_strict': False,
                    'schedule_saturday': [],
                    'licences_held': [],
                    'salary_preference': 'discuss',
                    'salary_amount': None,
                    'salary_currency': '',
                    'salary_period': '',
                    'salary_basis': '',
                    'acquired_skills': skills[:1],
                    'learning_activities': skills[1:2],
                },
            ),
            (
                'date',
                'Profil fictif C — date incompatible',
                {'available_from': timezone.localdate() + timedelta(days=40)},
            ),
            (
                'schedule',
                'Profil fictif D — horaires incompatibles',
                {
                    'schedule_saturday': [],
                    'schedule_monday': ['morning'],
                    'working_conditions': ['day'],
                },
            ),
            ('permit', 'Profil fictif E — autorisation absente', {'licences_held': []}),
        ]
        for key, name, changes in scenarios:
            user, _ = User.objects.get_or_create(
                email=key + '@matching-trial.invalid',
                defaults={'kind': 'candidate', 'is_active': True},
            )
            if user.kind != 'candidate' or not user.is_active:
                raise CommandError(
                    'Reserved fictional account is unavailable; no account changed.'
                )
            profile = CandidateProfile.objects.filter(user=user).first()
            if profile is None:
                values = dict(
                    display_name=name,
                    project_mode='open',
                    acquired_skills=skills,
                    professional_behaviours=behaviours,
                    desired_countries=['FR'],
                    mobility='discuss',
                    email_verified_at=timezone.now(),
                    language_skills={
                        'status': 'specified',
                        'languages': [{'code': 'fr', 'level': 'B1'}],
                    },
                    licences_held=['B'],
                    availability='date',
                    available_from=timezone.localdate() + timedelta(days=7),
                    contract_types=['permanent'],
                    working_time=['part'],
                    schedule_preference='specific',
                    schedule_strict=True,
                    schedule_saturday=['morning'],
                    working_conditions=['weekend'],
                    salary_preference='minimum',
                    salary_amount='18',
                    salary_currency='EUR',
                    salary_period='hour',
                    salary_basis='gross',
                )
                values.update(changes)
                profile = CandidateProfile.objects.create(user=user, **values)
            pair, _ = MatchPair.objects.get_or_create(
                candidate=profile,
                offer=offer,
                defaults={
                    'candidate_facts': (
                        {'licences_not_held_at_start': ['B']} if key == 'permit' else {}
                    )
                },
            )
            # Upgrade only the exact fictional facts created during this local recipe.
            if key == 'permit' and pair.candidate_facts == {'licences_not_held': ['B']}:
                pair.candidate_facts = {'licences_not_held_at_start': ['B']}
                pair.save(update_fields=['candidate_facts'])
            latest = pair.evaluations.order_by('-id').first()
            input_data, fingerprint = inputs(pair)
            if latest is None or latest.fingerprint != fingerprint:
                calculate(profile, offer)
        self.stdout.write(
            'Five fictional scenarios available; existing answers and decisions preserved.'
        )
