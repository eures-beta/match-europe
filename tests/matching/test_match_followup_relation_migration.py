"""The review is derived from the match, including after a populated rollback."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user
from tests.matching.test_schema_names import assert_schema_names


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class MatchFollowupRelationMigrationTests(TransactionTestCase):
    before = '0032_rename_match_followup'
    after = '0033_remove_match_followup_review'

    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', name)])
        return executor.loader.project_state([('matching', name)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_remove_and_reconstruct_link_without_losing_plans_or_events(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        reviewed = CandidateOfferMatch.objects.filter(
            candidate_offer_review__isnull=False
        ).first()
        unreviewed = CandidateOfferMatch.objects.filter(
            candidate_offer_review__isnull=True
        ).first()
        apps = self.migrate(self.before)
        Followup = apps.get_model('matching', 'MatchFollowup')
        records = []
        for match in (reviewed, unreviewed):
            review_id = (
                apps.get_model('matching', 'CandidateOfferReview')
                .objects.filter(match_id=match.pk)
                .values_list('pk', flat=True)
                .first()
            )
            row = Followup.objects.create(
                match_id=match.pk,
                review_id=review_id,
                next_action='Keep the plan',
                waiting_for='candidate',
                updated_by_adviser_id=adviser.pk,
            )
            event = apps.get_model('matching', 'MatchFollowupEvent').objects.create(
                followup=row,
                actor_id=adviser.pk,
                action='plan',
                snapshot={'next_action': 'Keep the plan'},
            )
            records.append((row.pk, event.pk, match.pk, review_id))
        for target in (self.after, self.before, self.after):
            apps = self.migrate(target)
            Followup = apps.get_model('matching', 'MatchFollowup')
            self.assertEqual(
                'review' in {f.name for f in Followup._meta.fields},
                target == self.before,
            )
            for pk, event_pk, match_pk, review_pk in records:
                row = Followup.objects.get(pk=pk)
                self.assertEqual(
                    (row.match_id, row.next_action), (match_pk, 'Keep the plan')
                )
                if target == self.before:
                    self.assertEqual(row.review_id, review_pk)
                self.assertEqual(
                    apps.get_model('matching', 'MatchFollowupEvent')
                    .objects.get(pk=event_pk)
                    .followup_id,
                    pk,
                )
            assert_schema_names(self, apps)
