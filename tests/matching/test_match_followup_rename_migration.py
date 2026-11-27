"""Exercise the follow-up rename forwards and backwards with connected data."""

from io import StringIO

from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user
from tests.matching.test_schema_names import assert_schema_names


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class MatchFollowupRenameMigrationTests(TransactionTestCase):
    before = '0031_alter_introductionfollowup_review'
    after = '0032_rename_match_followup'

    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', name)])
        return executor.loader.project_state([('matching', name)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def identity(self, table):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT %s::regclass::oid, pg_get_serial_sequence(%s, 'id')::regclass::oid",
                [table, table],
            )
            return cursor.fetchone()

    def test_round_trip_preserves_rows_relations_objects_and_role_guards(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.filter(
            candidate_offer_review__isnull=False
        ).first()
        review = match.candidate_offer_review
        apps = self.migrate(self.before)
        plan = apps.get_model('matching', 'IntroductionFollowup').objects.create(
            match_id=match.pk,
            review_id=review.pk,
            next_action='Call tomorrow',
            waiting_for='employer',
            updated_by_adviser_id=adviser.pk,
            version=7,
        )
        event = apps.get_model('matching', 'IntroductionFollowupEvent').objects.create(
            followup_id=plan.pk,
            actor_id=adviser.pk,
            action='reminder',
            message='Fictional reminder',
            snapshot={'version': 7},
            delivery_status='sent',
        )
        identities = [
            self.identity('matching_introductionfollowup' + suffix)
            for suffix in ('', 'event')
        ]
        for target in (self.after, self.before, self.after):
            apps = self.migrate(target)
            name = 'MatchFollowup' if target == self.after else 'IntroductionFollowup'
            Plan = apps.get_model('matching', name)
            Event = apps.get_model('matching', name + 'Event')
            saved = Plan.objects.get(pk=plan.pk)
            self.assertEqual(
                (saved.match_id, saved.review_id, saved.version, saved.next_action),
                (match.pk, review.pk, 7, 'Call tomorrow'),
            )
            history = Event.objects.get(pk=event.pk)
            self.assertEqual(
                (
                    history.followup_id,
                    history.message,
                    history.snapshot,
                    history.delivery_status,
                ),
                (plan.pk, 'Fictional reminder', {'version': 7}, 'sent'),
            )
            for model, identity in zip((Plan, Event), identities, strict=True):
                self.assertEqual(self.identity(model._meta.db_table), identity)
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT tgname FROM pg_trigger WHERE tgrelid = %s::regclass AND NOT tgisinternal',
                        [model._meta.db_table],
                    )
                    self.assertEqual(
                        cursor.fetchall(), [(model._meta.db_table + '_adviser_guard',)]
                    )
                    cursor.execute(
                        'SELECT count(*) FROM pg_proc WHERE proname = %s',
                        [model._meta.db_table + '_check_adviser'],
                    )
                    self.assertEqual(cursor.fetchone()[0], 1)
            assert_schema_names(self, apps)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Plan.objects.filter(pk=plan.pk).update(
                    updated_by_adviser_id=match.offer.employer_id
                )
            with self.assertRaises(IntegrityError), transaction.atomic():
                Event.objects.filter(pk=event.pk).update(
                    actor_id=match.offer.employer_id
                )
