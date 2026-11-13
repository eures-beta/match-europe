"""Upgrade the deployed confirmation schema without recreating its tables."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase, override_settings

from .fixtures.legacy_confirmations import Migration as LegacyMigration

OLD = '0003_confirmationrequest_confirmationanswer_and_more'
NEW = '0005_offer_confirmations'
NAMES = ('ConfirmationRequest', 'ConfirmationAnswer', 'TransmissionAgreement')


@override_settings(
    MATCHING_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    SHARED_DEMO=False,
)
class ConfirmationMigrationTests(TransactionTestCase):
    def setUp(self):
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()

    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', name)])
        return executor.loader.project_state([('matching', name)])

    def tearDown(self):
        # Only the isolated test DB: restore a clean current schema even if the
        # expected regression failed before Django could record the migration.
        # Unapply later model renames before manipulating the historical tables.
        if ('matching', '0006_candidate_offer_model_names') in (
            MigrationRecorder(connection).applied_migrations()
        ):
            self.migrate(NEW)
        recorder = MigrationRecorder(connection)
        recorder.record_unapplied('matching', OLD)
        state = MigrationExecutor(connection).loader.project_state([('matching', NEW)])
        with connection.schema_editor() as editor:
            for name in reversed(NAMES):
                model = state.apps.get_model('matching', name)
                if model._meta.db_table in connection.introspection.table_names():
                    editor.delete_model(model)
        recorder.record_unapplied('matching', NEW)
        MigrationExecutor(connection).migrate(self.leaves)
        super().tearDown()

    def legacy(self):
        state = self.migrate('0004_merge_offer_requirements')
        call_command('seed_matching_trial', stdout=StringIO())
        for operation in LegacyMigration.operations:
            operation.state_forwards('matching', state)
        with connection.schema_editor() as editor:
            for name in NAMES:
                editor.create_model(state.apps.get_model('matching', name))
        MigrationRecorder(connection).record_applied('matching', OLD)
        pair = state.apps.get_model('matching', 'MatchPair').objects.first()
        user = state.apps.get_model('users', 'User').objects.create(
            email='historical-adviser@example.invalid', kind='adviser'
        )
        request = state.apps.get_model('matching', NAMES[0]).objects.create(
            pair_id=pair.pk, requested_by_id=user.pk
        )
        state.apps.get_model('matching', NAMES[1]).objects.create(
            request_id=request.pk,
            actor_id=pair.candidate.user_id,
            question_key='fictional-condition',
            fingerprint='a' * 64,
            presented={'text': 'Fictional condition'},
            value='yes',
            detail='Confirmed',
        )
        state.apps.get_model('matching', NAMES[2]).objects.create(
            request_id=request.pk,
            actor_id=pair.candidate.user_id,
            fingerprint='b' * 64,
            agreed=True,
        )
        return state

    def snapshot(self):
        result = {}
        for name in (
            'confirmationrequest',
            'confirmationanswer',
            'transmissionagreement',
        ):
            table = 'matching_' + name
            with connection.cursor() as cursor:
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                result[table] = (oid, cursor.fetchall())
        return result

    def test_deployed_legacy_schema_preserves_rows_links_ids_dates_and_tables(self):
        self.legacy()
        before = self.snapshot()
        self.migrate(NEW)
        self.assertEqual(self.snapshot(), before)
        self.assertIn(
            ('matching', NEW), MigrationRecorder(connection).applied_migrations()
        )
        self.assertIn(
            ('matching', OLD), MigrationRecorder(connection).applied_migrations()
        )
        self.migrate('0004_merge_offer_requirements')
        self.assertEqual(self.snapshot(), before)
        state = self.migrate(NEW)
        self.assertEqual(self.snapshot(), before)
        Answer = state.apps.get_model('matching', 'ConfirmationAnswer')
        old = Answer.objects.first()
        new = Answer.objects.create(
            request_id=old.request_id,
            actor_id=old.actor_id,
            question_key='another-condition',
            fingerprint='c' * 64,
            presented={'text': 'Another condition'},
            value='yes',
            detail='',
        )
        self.assertGreater(new.pk, old.pk)

    def assert_refused(self, message='Legacy confirmation schema mismatch'):
        before = self.snapshot()
        with self.assertRaisesMessage(RuntimeError, message):
            self.migrate(NEW)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn(
            ('matching', NEW), MigrationRecorder(connection).applied_migrations()
        )

    def test_existing_tables_without_legacy_record_are_refused(self):
        self.legacy()
        MigrationRecorder(connection).record_unapplied('matching', OLD)
        self.assert_refused('Unexpected confirmation schema')

    def test_column_type_drift_is_refused_without_changing_rows(self):
        self.legacy()
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE matching_confirmationanswer ALTER COLUMN question_key TYPE varchar(249)'
            )
        self.assert_refused()

    def test_nullable_column_drift_is_refused_without_changing_rows(self):
        self.legacy()
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE matching_confirmationanswer ALTER COLUMN question_key DROP NOT NULL'
            )
        self.assert_refused()

    def test_missing_foreign_key_is_refused_without_changing_rows(self):
        self.legacy()
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, 'matching_confirmationanswer'
            )
            name = next(
                name for name, value in constraints.items() if value['foreign_key']
            )
            cursor.execute(
                'ALTER TABLE matching_confirmationanswer DROP CONSTRAINT '
                + connection.ops.quote_name(name)
            )
        self.assert_refused()

    def test_missing_uniqueness_is_refused_without_changing_rows(self):
        self.legacy()
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, 'matching_confirmationrequest'
            )
            name = next(
                name
                for name, value in constraints.items()
                if value['unique'] and not value['primary_key']
            )
            cursor.execute(
                'ALTER TABLE matching_confirmationrequest DROP CONSTRAINT '
                + connection.ops.quote_name(name)
            )
        self.assert_refused()

    def test_partial_schema_is_refused(self):
        state = self.legacy()
        Request = state.apps.get_model('matching', 'ConfirmationRequest')
        before = list(Request.objects.values())
        with connection.schema_editor() as editor:
            editor.delete_model(
                state.apps.get_model('matching', 'TransmissionAgreement')
            )
        with self.assertRaisesMessage(RuntimeError, 'Unexpected confirmation schema'):
            self.migrate(NEW)
        self.assertEqual(list(Request.objects.values()), before)

    def test_empty_schema_with_legacy_record_is_refused(self):
        state = self.legacy()
        with connection.schema_editor() as editor:
            for name in reversed(NAMES):
                editor.delete_model(state.apps.get_model('matching', name))
        with self.assertRaisesMessage(RuntimeError, 'Unexpected confirmation schema'):
            self.migrate(NEW)

    def test_fresh_schema_can_be_created_reversed_and_created_again(self):
        self.migrate('0004_merge_offer_requirements')
        state = self.migrate(NEW)
        tables = {
            state.apps.get_model('matching', name)._meta.db_table for name in NAMES
        }
        self.assertTrue(tables <= set(connection.introspection.table_names()))
        self.migrate('0004_merge_offer_requirements')
        self.assertFalse(tables & set(connection.introspection.table_names()))
        self.migrate(NEW)
        self.assertTrue(tables <= set(connection.introspection.table_names()))
