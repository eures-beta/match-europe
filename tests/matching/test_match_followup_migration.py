from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from eures_beta.introductions import offer_review_services
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user
from tests.matching.test_schema_names import assert_schema_names


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class IntroductionFollowupMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_migration_preserves_existing_dossier_and_names(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        match.decision = 'retained'
        match.save()
        review = offer_review_services.request_offer_review(adviser, match.pk)
        self.migrate('0025_employer_consent_database_names')
        apps = self.migrate('0026_introductionfollowup_introductionfollowupevent')
        plan = apps.get_model('matching', 'IntroductionFollowup').objects.create(
            review_id=review.pk,
            next_action='Arrange interview',
            waiting_for='employer',
            updated_by_adviser_id=adviser.pk,
        )
        event = apps.get_model('matching', 'IntroductionFollowupEvent').objects.create(
            followup_id=plan.pk,
            actor_id=adviser.pk,
            action='plan',
            snapshot={'next_action': 'Arrange interview'},
        )
        for target in (
            '0027_followup_database_names',
            '0026_introductionfollowup_introductionfollowupevent',
            '0027_followup_database_names',
        ):
            apps = self.migrate(target)
            row = apps.get_model('matching', 'IntroductionFollowup').objects.get(
                pk=plan.pk
            )
            self.assertEqual(row.review_id, review.pk)
            self.assertEqual(row.next_action, 'Arrange interview')
            self.assertTrue(
                apps.get_model('matching', 'IntroductionFollowupEvent')
                .objects.filter(pk=event.pk)
                .exists()
            )
        assert_schema_names(self, apps)
        apps = self.migrate('0025_employer_consent_database_names')
        self.assertTrue(
            apps.get_model('matching', 'CandidateOfferReview')
            .objects.filter(pk=review.pk)
            .exists()
        )
        self.assertNotIn(
            'matching_introductionfollowup', connection.introspection.table_names()
        )
