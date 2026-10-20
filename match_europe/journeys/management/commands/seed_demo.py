from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from journeys.models import Candidate, Offer, Profile, Question
from journeys.services import dispatch_offer, suggest_candidates


class Command(BaseCommand):
    help = 'Create fictional demonstration data, without sending emails or external requests.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError('Demonstration mode required.')
        users = {}
        for role, name in [('adviser', 'Camille demo'), ('employer', 'Horizon company demo'),
                           ('candidate', 'Alex demo'), ('admin', 'Administration demo')]:
            user, created = User.objects.get_or_create(username=f'{role}@example.invalid', defaults={'email': f'{role}@example.invalid'})
            if created:
                user.set_unusable_password()
                user.save()
            Profile.objects.get_or_create(user=user, defaults={'role': role, 'name': name, 'verified': True})
            users[role] = user
        for role in ['employer', 'candidate']:
            profile = users[role].profile
            profile.adviser = users['adviser']
            profile.save()
        offer, _ = Offer.objects.get_or_create(employer=users['employer'], title='Cleaner demonstration',
            defaults={'adviser': users['adviser'], 'company': 'Horizon company (fictional)', 'location': 'Luxembourg',
                      'description': 'Fictional company: office cleaning, Monday to Friday, starting at 6 am. Teamwork.',
                      'contract': 'Permanent contract demonstration', 'salary': 'To clarify', 'hours': '35 hours per week',
                      'languages': 'English: workplace communication', 'skills': 'Office cleaning',
                      'cross_border': 'yes', 'relocation': 'discuss', 'validated_at': timezone.now(), 'state': 'ready'})
        for position, (text, expectation, choices) in enumerate([
            ('When could you start?', 'Clarify availability with the adviser', 'Now|In two weeks|In one month'),
            ('Can you reach the workplace at 6 am?', '6 am arrival required; clarify transport', 'Yes|No|To discuss'),
            ('Describe your office cleaning experience.', 'Review relevant experience or training needs', '')]):
            Question.objects.get_or_create(offer=offer, position=position, defaults={'text': text, 'expectation': expectation, 'options': choices})
        Candidate.objects.get_or_create(user=users['candidate'], defaults={'name': 'Alex fictional profile',
            'experience': 'Two years cleaning offices: fictional data.', 'jobs': 'Office cleaning',
            'skills': 'Office cleaning, teamwork', 'languages': 'English', 'location': 'Arlon',
            'availability': 'In two weeks', 'cross_border': 'yes', 'relocation': 'discuss',
            'validated_at': timezone.now(), 'sent_at': timezone.now()})
        dispatch_offer(offer, users['employer'])
        suggest_candidates(offer, users['adviser'])
        self.stdout.write(self.style.SUCCESS('Four fictional roles and an end-to-end scenario are ready.'))
