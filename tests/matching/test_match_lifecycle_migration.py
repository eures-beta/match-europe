from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from eures_beta.matching import match_lifecycle
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user
from .test_schema_names import assert_schema_names


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class MatchingLifeLineMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', name)])
        return executor.loader.project_state([('matching', name)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def prepare(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        return prepared_user('adviser')

    def test_existing_plan_and_history_are_attached_to_the_same_matching_in_both_directions(
        self,
    ):
        adviser = self.prepare()
        review = (
            CandidateOfferMatch.objects.filter(candidate_offer_review__isnull=False)
            .first()
            .candidate_offer_review
        )
        match_id, review_id = review.match_id, review.pk
        apps = self.migrate('0027_followup_database_names')
        plan = apps.get_model('matching', 'IntroductionFollowup').objects.create(
            review_id=review_id,
            next_action='Keep this action',
            waiting_for='candidate',
            updated_by_adviser_id=adviser.pk,
            due_on=timezone.localdate(),
        )
        event = apps.get_model('matching', 'IntroductionFollowupEvent').objects.create(
            followup_id=plan.pk,
            actor_id=adviser.pk,
            action='plan',
            snapshot={'next_action': 'Keep this action'},
        )
        for target in (
            '0031_alter_introductionfollowup_review',
            '0027_followup_database_names',
            '0031_alter_introductionfollowup_review',
        ):
            apps = self.migrate(target)
            saved = apps.get_model('matching', 'IntroductionFollowup').objects.get(
                pk=plan.pk
            )
            self.assertEqual(saved.review_id, review_id)
            self.assertEqual(saved.next_action, 'Keep this action')
            self.assertEqual(saved.due_on, plan.due_on)
            self.assertTrue(
                apps.get_model('matching', 'IntroductionFollowupEvent')
                .objects.filter(pk=event.pk)
                .exists()
            )
            if target.startswith('0031'):
                self.assertEqual(saved.match_id, match_id)
                assert_schema_names(self, apps)

    def test_rollback_refuses_to_discard_a_plan_created_before_candidate_review(self):
        adviser = self.prepare()
        match = CandidateOfferMatch.objects.filter(
            candidate_offer_review__isnull=True
        ).first()
        plan = match_lifecycle.schedule(
            adviser, match.pk, due_on=timezone.localdate(), version=0
        )
        with self.assertRaisesMessage(
            RuntimeError, 'Cannot roll back plans created before'
        ):
            self.migrate('0027_followup_database_names')
        apps = self.migrate('0031_alter_introductionfollowup_review')
        self.assertEqual(
            apps.get_model('matching', 'IntroductionFollowup')
            .objects.get(pk=plan.pk)
            .match_id,
            match.pk,
        )

    def test_rollback_refuses_to_drop_a_declared_outcome(self):
        adviser = self.prepare()
        match = CandidateOfferMatch.objects.first()
        result = match_lifecycle.conclude(
            adviser, match.pk, 'stopped', 0, reason='Keep this conclusion'
        )
        with self.assertRaisesMessage(
            RuntimeError, 'Cannot roll back declared matching outcomes'
        ):
            self.migrate('0027_followup_database_names')
        from eures_beta.matching.models import MatchConclusion

        self.assertEqual(
            MatchConclusion.objects.get(pk=result.pk).reason, 'Keep this conclusion'
        )
