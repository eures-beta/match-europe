"""Explicit fixtures, with no reassignment, privilege reset or real message."""

from copy import deepcopy
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user
from eures_beta.candidates.models import CandidateProfile
from eures_beta.candidates.skill_choices import skill_groups
from eures_beta.employers.models import JobOffer
from eures_beta.matching.team_access import team_enabled
from eures_beta.matching.access import test_data_enabled
from eures_beta.matching.models import (
    MatchingTeam,
    TeamMembership,
    TeamOffer,
    TeamCandidate,
    MatchPair,
)
from eures_beta.matching.services import calculate, inputs


class Command(BaseCommand):
    help = 'Prepare isolated team matching with fictional accounts only.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not team_enabled() or not test_data_enabled():
            raise CommandError(
                'Local team matching and fictional accounts must be explicitly enabled.'
            )
        call_command('seed_test_accounts', stdout=self.stdout)
        call_command('seed_matching_trial', stdout=self.stdout)
        primary, _ = MatchingTeam.objects.get_or_create(
            slug='trial-main', defaults={'name': 'Equipe fictive A'}
        )
        outside, _ = MatchingTeam.objects.get_or_create(
            slug='trial-other', defaults={'name': 'Equipe fictive B'}
        )
        for key, team, first_name in [
            ('adviser', primary, 'Conseiller A'),
            ('matching-peer', primary, 'Conseiller B'),
            ('matching-other', outside, 'Conseiller autre equipe'),
        ]:
            user = prepared_user(key)
            if not user:
                raise CommandError('Fictional adviser unavailable; nothing changed.')
            if not user.first_name:
                user.first_name = first_name
                user.save(update_fields=['first_name'])
            # Existing grants, including revoked/read-only ones, are never reset.
            TeamMembership.objects.get_or_create(
                team=team, user=user, defaults={'can_decide': True}
            )
        offer = JobOffer.objects.get(
            email='employer@matching-trial.invalid', source_kind='matching'
        )
        assignment, _ = TeamOffer.objects.get_or_create(
            offer=offer, defaults={'team': primary}
        )
        if assignment.team_id != primary.pk:
            raise CommandError(
                'The fictional offer already belongs to a different team.'
            )
        for key in ('compatible', 'unknown', 'date', 'schedule', 'permit'):
            candidate = CandidateProfile.objects.get(
                user__email=key + '@matching-trial.invalid'
            )
            TeamCandidate.objects.get_or_create(team=primary, candidate=candidate)
            pair = MatchPair.objects.get(candidate=candidate, offer=offer)
            if pair.team_id not in (None, primary.pk):
                raise CommandError(
                    'A fictional pair was reassigned; no assignment overwritten.'
                )
            if pair.team_id is None:
                pair.team = primary
                pair.save(update_fields=['team'])
        base = CandidateProfile.objects.get(
            user__email='compatible@matching-trial.invalid'
        )
        excluded = {'id', 'user', 'created_at', 'updated_at'}
        values = {
            field.name: deepcopy(getattr(base, field.name))
            for field in base._meta.fields
            if field.name not in excluded
        }
        values.update(
            display_name='Profil fictif F - score nul',
            desired_countries=['DE'],
            acquired_skills=[],
            learning_activities=[],
            occupation_skills={},
            licences_held=[],
            availability='discuss',
            available_from=None,
            contract_types=['fixed'],
            working_conditions=['day'],
            schedule_preference='discuss',
            schedule_strict=False,
            salary_amount=50,
            language_skills={
                'status': 'specified',
                'languages': [{'code': 'fr', 'level': 'A1'}],
            },
        )
        expected = {
            uri
            for selection in offer.data.get('occupationSkills', {}).values()
            for uri in selection.get('skills', [])
        }
        values['acquired_skills'] = [
            next(
                uri
                for uri in skill_groups()[0]['acquired_skills']
                if uri not in expected
            )
        ]
        for day in (
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday',
        ):
            values['schedule_' + day] = []
        user, _ = User.objects.get_or_create(
            email='manual-zero@matching-trial.invalid', defaults={'kind': 'candidate'}
        )
        if user.kind != 'candidate' or not user.is_active:
            raise CommandError('Reserved candidate unavailable.')
        candidate, _ = CandidateProfile.objects.get_or_create(
            user=user, defaults=values
        )
        TeamCandidate.objects.get_or_create(team=primary, candidate=candidate)
        pair, _ = MatchPair.objects.get_or_create(
            candidate=candidate, offer=offer, defaults={'team': primary}
        )
        if pair.team_id != primary.pk:
            raise CommandError('The manual example already belongs to another team.')
        if not pair.evaluations.exists():
            calculate(candidate, offer)
        # An isolated second portfolio makes cross-team access testable.
        other_user, _ = User.objects.get_or_create(
            email='outside@matching-trial.invalid', defaults={'kind': 'candidate'}
        )
        if other_user.kind != 'candidate' or not other_user.is_active:
            raise CommandError('Reserved candidate unavailable.')
        outside_values = {
            field.name: deepcopy(getattr(base, field.name))
            for field in base._meta.fields
            if field.name not in excluded
        }
        outside_values['display_name'] = 'Profil fictif - autre equipe'
        outside_candidate, _ = CandidateProfile.objects.get_or_create(
            user=other_user, defaults=outside_values
        )
        other_offer = JobOffer.objects.filter(
            source_kind='matchother', email=offer.email
        ).first()
        if not other_offer:
            data = deepcopy(offer.data)
            data['title'] = 'Offre fictive - autre equipe'
            other_offer = JobOffer.objects.create(
                created_by=offer.created_by,
                email=offer.email,
                session_key='matching-team-trial',
                preparation_agreed_at=timezone.now(),
                validated_at=timezone.now(),
                source_kind='matchother',
                data=data,
            )
        other_assignment, _ = TeamOffer.objects.get_or_create(
            offer=other_offer, defaults={'team': outside}
        )
        if other_assignment.team_id != outside.pk:
            raise CommandError('Outside offer already reassigned.')
        TeamCandidate.objects.get_or_create(team=outside, candidate=outside_candidate)
        pair, _ = MatchPair.objects.get_or_create(
            candidate=outside_candidate, offer=other_offer, defaults={'team': outside}
        )
        if pair.team_id != outside.pk:
            raise CommandError('Outside pair already reassigned.')
        if not pair.evaluations.exists():
            calculate(outside_candidate, other_offer)
        self.stdout.write(
            'Two shared advisers, one isolated adviser and a zero-score example are ready.'
        )
