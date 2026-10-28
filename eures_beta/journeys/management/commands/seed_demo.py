from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer, Question
from eures_beta.journeys.models import Profile
from eures_beta.journeys.services import dispatch_offer, suggest_candidates


class Command(BaseCommand):
    help = 'Create fictional demonstration data, without sending emails or external requests.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError('Demonstration mode required.')
        users = {}
        for role, name in [
            ('adviser', 'Camille · démo'),
            ('employer', 'Entreprise Horizon · démo'),
            ('candidate', 'Alex · démo'),
            ('admin', 'Administration · démo'),
        ]:
            user, created = User.objects.get_or_create(
                username=f'{role}@example.invalid',
                defaults={'email': f'{role}@example.invalid'},
            )
            if created:
                user.set_unusable_password()
                user.save()
            Profile.objects.get_or_create(
                user=user, defaults={'role': role, 'name': name, 'verified': True}
            )
            users[role] = user
        for role in ['employer', 'candidate']:
            profile = users[role].profile
            profile.adviser = users['adviser']
            profile.save()
        offer, _ = Offer.objects.get_or_create(
            employer=users['employer'],
            title='Agent / Agente d’entretien — démonstration',
            defaults={
                'adviser': users['adviser'],
                'company': 'Entreprise Horizon (fictive)',
                'location': 'Luxembourg',
                'description': 'Entreprise fictive : entretien de bureaux, du lundi au vendredi, prise de poste à 6 h. Travail en équipe.',
                'contract': 'CDI · démonstration',
                'salary': 'À préciser',
                'hours': '35 h / semaine',
                'languages': 'Français : communication de travail',
                'skills': 'Entretien de locaux',
                'cross_border': 'yes',
                'relocation': 'discuss',
                'validated_at': timezone.now(),
                'state': 'ready',
            },
        )
        for position, (text, expectation, choices) in enumerate(
            [
                (
                    'À partir de quand pourriez-vous commencer ?',
                    'Disponibilité à préciser avec le conseiller',
                    'Dès maintenant|Sous deux semaines|Sous un mois',
                ),
                (
                    'Pouvez-vous rejoindre le lieu de travail à 6 h ?',
                    'Présence à 6 h indispensable, transport à clarifier',
                    'Oui|Non|À discuter',
                ),
                (
                    'Décrivez votre expérience en entretien de locaux.',
                    'Expérience pertinente ou besoin de formation à examiner',
                    '',
                ),
            ]
        ):
            Question.objects.get_or_create(
                offer=offer,
                position=position,
                defaults={'text': text, 'expectation': expectation, 'options': choices},
            )
        Candidate.objects.get_or_create(
            user=users['candidate'],
            defaults={
                'name': 'Alex · profil fictif',
                'experience': 'Deux ans en entretien de bureaux — données fictives.',
                'jobs': 'Entretien de locaux',
                'skills': 'Nettoyage de bureaux, travail en équipe',
                'languages': 'Français',
                'location': 'Arlon',
                'availability': 'Sous deux semaines',
                'cross_border': 'yes',
                'relocation': 'discuss',
                'validated_at': timezone.now(),
                'sent_at': timezone.now(),
            },
        )
        dispatch_offer(offer, users['employer'])
        suggest_candidates(offer, users['adviser'])
        self.stdout.write(
            self.style.SUCCESS(
                'Four fictional roles and an end-to-end scenario are ready.'
            )
        )
