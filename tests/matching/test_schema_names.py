"""PostgreSQL rename round-trip with nonempty, connected business records."""

from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection, DatabaseError, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.apps import apps as current_apps

from tests.matching.fixtures.historical import seed_matching
from tests.common.migration_state import historical_targets, prepare_historical

NAMES = import_module('eures_beta.matching.migrations.0011_harmonize_database_objects')
BEFORE = historical_targets([('matching', '0008_sharedconversation_sharedmessage')])
AFTER = [('matching', '0011_harmonize_database_objects')]


class SchemaNamingMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        if targets == BEFORE:
            prepare_historical(connection)
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def snapshot(self, apps):
        result = {}
        with connection.cursor() as cursor:
            for model in apps.get_models(include_auto_created=True):
                if model._meta.app_label not in NAMES.APPS:
                    continue
                table = model._meta.db_table
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY 1'
                )
                rows = cursor.fetchall()
                sequences = []
                for field in model._meta.local_fields:
                    cursor.execute(
                        'SELECT pg_get_serial_sequence(%s, %s)::regclass::oid',
                        [table, field.column],
                    )
                    sequence = cursor.fetchone()[0]
                    if sequence:
                        cursor.execute(
                            'SELECT last_value FROM pg_sequences WHERE schemaname=current_schema() AND sequencename=(SELECT relname FROM pg_class WHERE oid=%s)',
                            [sequence],
                        )
                        sequences.append((sequence, cursor.fetchone()[0]))
                label = {
                    'matching.sharedconversation': 'matching.candidateofferconversation',
                    'matching.sharedmessage': 'matching.candidateofferconversationmessage',
                }.get(model._meta.label_lower, model._meta.label_lower)
                result[label] = (oid, rows, sequences)
        return result

    def prepare(self, apps):
        match = seed_matching(apps)
        get = apps.get_model
        adviser = get('users', 'User').objects.create(
            email='schema-adviser@example.invalid', kind='adviser'
        )
        company = get('employers', 'Company').objects.create(name='Fictional company')
        get('employers', 'CompanyMembership').objects.create(
            company=company, person=match.offer.created_by
        )
        get('employers', 'JobOffer').objects.filter(pk=match.offer_id).update(
            company=company
        )
        get('employers', 'EmployerProfile').objects.create(
            user=match.offer.created_by,
            response_coverage='all',
            response_time='under_week',
        )
        get('candidates', 'CandidatePushSubscription').objects.create(
            candidate=match.candidate,
            endpoint='https://push.example.invalid/fictional',
            keys={'p256dh': 'fictional'},
        )
        get('invitations', 'Invitation').objects.create(
            sender=adviser, email='invited@example.invalid'
        )
        get('skills', 'OccupationSkillSuggestion').objects.create(
            occupation_uri='urn:fictional', source_version='1', method='fictional'
        )
        evaluation = match.evaluations.get()
        get('matching', 'MatchDecision').objects.create(
            pair=match, evaluation=evaluation, value='retained'
        )
        review = get('matching', 'CandidateOfferReview').objects.create(
            pair=match, requested_by=adviser
        )
        get('matching', 'CandidateOfferReviewAnswer').objects.create(
            request=review,
            actor=match.candidate.user,
            question_key='fictional',
            fingerprint='a' * 64,
            presented={},
            value='yes',
            dialogue={'preserve': True},
        )
        get('matching', 'CandidateProfileSharing').objects.create(
            request=review,
            actor=match.candidate.user,
            fingerprint='b' * 64,
            agreed=True,
        )
        conversation = get('matching', 'SharedConversation').objects.create(
            confirmation=review,
            adviser=adviser,
            candidate=match.candidate.user,
            employer=match.offer.created_by,
            introduction='Fictional',
            state='open',
        )
        get('matching', 'SharedMessage').objects.create(
            conversation=conversation, author=adviser, body='Preserve this message'
        )
        return match.pk

    def test_nonempty_round_trip_preserves_rows_oids_sequences_permissions_and_guards(
        self,
    ):
        apps = self.migrate(BEFORE)
        match_id = self.prepare(apps)
        content_type, _ = ContentType.objects.get_or_create(
            app_label='matching', model='candidateoffermatch'
        )
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_candidateoffermatch',
            defaults={'name': 'Fictional permission'},
        )
        group = Group.objects.create(name='fictional-schema-observers')
        group.permissions.add(permission)
        expected = self.snapshot(apps)
        for targets in (AFTER, BEFORE, AFTER):
            apps = self.migrate(targets)
            self.assertEqual(self.snapshot(apps), expected)
            self.assertTrue(
                group.permissions.filter(
                    pk=permission.pk, content_type_id=content_type.pk
                ).exists()
            )
            if targets == AFTER:
                assert_schema_names(self, apps)
                Match = apps.get_model('matching', 'CandidateOfferMatch')
                match = Match.objects.get(pk=match_id)
                self.assertEqual(match.evaluations.get().match_id, match_id)
                self.assertTrue(
                    match.candidate_offer_review.profile_sharings.get().agreed
                )
                self.assertEqual(
                    match.candidate_offer_review.candidate_offer_conversation.messages.get().body,
                    'Preserve this message',
                )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Match.objects.create(
                candidate_id=match.candidate_id, offer_id=match.offer_id
            )
        user = apps.get_model('users', 'User').objects.get(pk=match.candidate.user_id)
        with self.assertRaises(DatabaseError), transaction.atomic():
            type(user).objects.filter(pk=user.pk).update(kind='employer')
        Answer = apps.get_model('matching', 'CandidateOfferReviewAnswer')
        previous = Answer.objects.get()
        next_answer = Answer.objects.create(
            review_id=previous.review_id,
            actor_id=previous.actor_id,
            question_key='next',
            fingerprint='c' * 64,
            presented={},
            value='no',
        )
        self.assertGreater(next_answer.pk, previous.pk)


def assert_schema_names(test, apps):
    with connection.cursor() as cursor:
        for model in apps.get_models(include_auto_created=True):
            if not apps.get_app_config(model._meta.app_label).name.startswith(
                'eures_beta.'
            ):
                continue
            table = model._meta.db_table
            test.assertEqual(table, f'{model._meta.app_label}_{model._meta.model_name}')
            for name in connection.introspection.get_constraints(cursor, table):
                test.assertTrue(
                    name.startswith(table + '_')
                    or name in {index.name for index in model._meta.indexes},
                    (table, name),
                )
                test.assertLessEqual(len(name), 63)

            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='n'",
                [table],
            )
            for (name,) in cursor.fetchall():
                test.assertTrue(name.startswith(table + '_'), (table, name))
                test.assertLessEqual(len(name), 63)

            for field in model._meta.local_fields:
                cursor.execute(
                    'SELECT c.relname FROM pg_class c WHERE c.oid=pg_get_serial_sequence(%s,%s)::regclass',
                    [table, field.column],
                )
                sequence = cursor.fetchone()
                if sequence:
                    test.assertTrue(sequence[0].startswith(table + '_'), sequence)
            cursor.execute(
                'SELECT tgname FROM pg_trigger WHERE tgrelid=%s::regclass AND NOT tgisinternal',
                [table],
            )
            for (name,) in cursor.fetchall():
                test.assertTrue(name.startswith(table + '_'), name)


class CurrentSchemaNamesTests(TestCase):
    def test_all_project_database_objects_follow_current_model_names(self):
        assert_schema_names(self, current_apps)
