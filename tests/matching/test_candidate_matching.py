from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from eures_beta.candidates import registration
from eures_beta.matching import services
from eures_beta.matching.models import CandidateOfferMatch, MatchEvaluation
from eures_beta.users.models import User
from tests.candidates.test_registration import answers


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    DJANGO_ENVIRONMENT='local',
)
class CandidateMatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_matching_trial', stdout=StringIO())

    def setUp(self):
        self.user = User.objects.create_user(
            'new@candidate-matching.invalid', kind='candidate'
        )

    def create_profile(self):
        return registration.create_verified_profile(
            self.user, answers(), 'fr', timezone.now()
        )

    def test_verified_profile_matches_existing_offers_only_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.assertTrue(self.create_profile())
            self.assertFalse(
                CandidateOfferMatch.objects.filter(candidate__user=self.user).exists()
            )
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(
            CandidateOfferMatch.objects.filter(candidate__user=self.user).exists()
        )

    def test_existing_profile_is_not_replaced_or_scheduled(self):
        self.create_profile()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.assertFalse(self.create_profile())
        self.assertEqual(callbacks, [])

    def test_update_recalculates_and_preserves_human_decision(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.create_profile()
        match = CandidateOfferMatch.objects.filter(candidate__user=self.user).first()
        match.decision = 'refused'
        match.save(update_fields=['decision'])
        previous = match.evaluations.count()
        with self.captureOnCommitCallbacks(execute=True):
            registration.update_profile(
                self.user,
                {**answers(), 'desired_occupations': 'Changed fictional job'},
                'de',
            )
        match.refresh_from_db()
        self.assertEqual(match.decision, 'refused')
        self.assertEqual(match.evaluations.count(), previous + 1)
        count = MatchEvaluation.objects.count()
        services.calculate_for_saved_candidate(match.candidate_id)
        self.assertEqual(MatchEvaluation.objects.count(), count)

    def test_matching_works_in_all_environments_without_demo_accounts(self):
        self.create_profile()
        profile = self.user.candidate_profile
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment, DEMO_ACCOUNTS_ENABLED=False
                ),
                self.captureOnCommitCallbacks(execute=True),
            ):
                registration.update_profile(self.user, answers(), 'fr')
            self.assertTrue(
                CandidateOfferMatch.objects.filter(candidate=profile).exists()
            )

    def test_rollback_does_not_calculate(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    self.create_profile()
                    raise ValueError('rollback')
            except ValueError:
                pass
        self.assertEqual(callbacks, [])
        self.assertFalse(
            CandidateOfferMatch.objects.filter(candidate__user=self.user).exists()
        )

    def test_candidate_no_longer_eligible_is_ignored(self):
        self.create_profile()
        profile = self.user.candidate_profile
        profile.email_verified_at = None
        profile.save()
        services.calculate_for_saved_candidate(profile.pk)
        self.assertFalse(CandidateOfferMatch.objects.filter(candidate=profile).exists())
        profile.email_verified_at = timezone.now()
        profile.save()
        self.user.is_active = False
        self.user.save()
        services.calculate_for_saved_candidate(profile.pk)
        self.assertFalse(CandidateOfferMatch.objects.filter(candidate=profile).exists())

    def test_ineligible_offer_is_ignored(self):
        self.create_profile()
        match = CandidateOfferMatch.objects.first()
        match.offer.created_by.is_active = False
        match.offer.created_by.save()
        services.calculate_for_saved_candidate(self.user.candidate_profile.pk)
        self.assertFalse(
            CandidateOfferMatch.objects.filter(candidate__user=self.user).exists()
        )

    def test_matching_failure_does_not_undo_profile(self):
        with patch.object(
            services,
            'calculate_for_saved_candidate',
            side_effect=RuntimeError('unavailable'),
        ):
            with (
                self.assertLogs('django.test', level='ERROR'),
                self.captureOnCommitCallbacks(execute=True),
            ):
                self.create_profile()
        self.assertTrue(hasattr(self.user, 'candidate_profile'))
