"""Preserve old preview conversations while extending the current migration graph."""

from importlib import import_module
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

BRIDGE = import_module(
    'eures_beta.matching.migrations.0008_sharedconversation_sharedmessage'
)
BEFORE = '0007_candidate_offer_review_answer_dialogue'
AFTER = '0008_sharedconversation_sharedmessage'


@override_settings(
    MATCHING_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class SharedConversationMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        apps = self.migrate(BEFORE)
        MigrationRecorder(connection).record_unapplied('matching', BRIDGE.LEGACY)
        present = set(connection.introspection.table_names())
        with connection.schema_editor() as editor:
            for model in reversed(BRIDGE.conversation_models(apps)):
                if model._meta.db_table in present:
                    editor.delete_model(model)
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def prepare(self):
        apps = self.migrate(BEFORE)
        call_command('seed_matching_trial', stdout=StringIO())
        pair = apps.get_model('matching', 'CandidateOfferMatch').objects.first()
        adviser = apps.get_model('users', 'User').objects.create(
            email='shared-migration@example.invalid', kind='adviser'
        )
        review = apps.get_model('matching', 'CandidateOfferReview').objects.create(
            pair_id=pair.pk, requested_by_id=adviser.pk
        )
        return (
            apps,
            review.pk,
            adviser.pk,
            pair.candidate.user_id,
            pair.offer.created_by_id,
        )

    def populate(self, conversation_model, message_model, fixture):
        _, review, adviser, candidate, employer = fixture
        thread = conversation_model.objects.create(
            confirmation_id=review,
            adviser_id=adviser,
            candidate_id=candidate,
            employer_id=employer,
            state='open',
            introduction='Fictional introduction',
            consent_at=timezone.now(),
            adviser_read=7,
            candidate_read=3,
            employer_read=2,
        )
        message = message_model.objects.create(
            conversation_id=thread.pk,
            author_id=candidate,
            body='Preserved fictional reply',
        )
        return thread.pk, message.pk

    def legacy(self, fixture):
        models = BRIDGE.conversation_models(fixture[0])
        with connection.schema_editor() as editor:
            for model in models:
                editor.create_model(model)
        MigrationRecorder(connection).record_applied('matching', BRIDGE.LEGACY)
        return models

    def snapshot(self):
        result = {}
        with connection.cursor() as cursor:
            for table in ('matching_sharedconversation', 'matching_sharedmessage'):
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                result[table] = oid, cursor.fetchall()
        return result

    def test_fresh_install_relationships_and_rollback(self):
        fixture = self.prepare()
        apps = self.migrate(AFTER)
        conversation = apps.get_model('matching', 'SharedConversation')
        message = apps.get_model('matching', 'SharedMessage')
        thread_id, message_id = self.populate(conversation, message, fixture)
        self.assertEqual(
            conversation.objects.get(pk=thread_id).confirmation_id, fixture[1]
        )
        self.assertEqual(message.objects.get(pk=message_id).conversation_id, thread_id)
        self.migrate(BEFORE)
        self.assertNotIn(
            'matching_sharedconversation', connection.introspection.table_names()
        )
        self.assertTrue(
            fixture[0]
            .get_model('matching', 'CandidateOfferReview')
            .objects.filter(pk=fixture[1])
            .exists()
        )
        self.migrate(AFTER)

    def test_legacy_tables_rows_relations_and_sequences_are_preserved(self):
        fixture = self.prepare()
        conversation, message = self.legacy(fixture)
        _, message_id = self.populate(conversation, message, fixture)
        expected = self.snapshot()
        apps = self.migrate(AFTER)
        self.assertEqual(self.snapshot(), expected)
        self.migrate(BEFORE)
        self.assertEqual(self.snapshot(), expected)
        apps = self.migrate(AFTER)
        self.assertEqual(self.snapshot(), expected)
        model = apps.get_model('matching', 'SharedMessage')
        previous = model.objects.get(pk=message_id)
        later = model.objects.create(
            conversation_id=previous.conversation_id,
            author_id=previous.author_id,
            body='Next reply',
        )
        self.assertGreater(later.pk, message_id)

    def test_unrecorded_tables_are_refused_without_losing_rows(self):
        fixture = self.prepare()
        models = self.legacy(fixture)
        self.populate(*models, fixture)
        MigrationRecorder(connection).record_unapplied('matching', BRIDGE.LEGACY)
        expected = self.snapshot()
        with self.assertRaisesMessage(
            RuntimeError, 'Unexpected shared conversation schema'
        ):
            self.migrate(AFTER)
        self.assertEqual(self.snapshot(), expected)

    def test_partial_legacy_tables_are_refused(self):
        fixture = self.prepare()
        conversation = BRIDGE.conversation_models(fixture[0])[0]
        with connection.schema_editor() as editor:
            editor.create_model(conversation)
        MigrationRecorder(connection).record_applied('matching', BRIDGE.LEGACY)
        with self.assertRaisesMessage(
            RuntimeError, 'Unexpected shared conversation schema'
        ):
            self.migrate(AFTER)

    def test_wrong_column_is_refused_without_losing_rows(self):
        fixture = self.prepare()
        self.populate(*self.legacy(fixture), fixture)
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE matching_sharedmessage ALTER COLUMN body TYPE varchar(2000)'
            )
        expected = self.snapshot()
        with self.assertRaisesMessage(RuntimeError, 'schema mismatch'):
            self.migrate(AFTER)
        self.assertEqual(self.snapshot(), expected)

    def test_wrong_check_constraint_is_refused(self):
        fixture = self.prepare()
        self.populate(*self.legacy(fixture), fixture)
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE matching_sharedconversation ADD CONSTRAINT unexpected_check CHECK (adviser_read < 1000)'
            )
        expected = self.snapshot()
        with self.assertRaisesMessage(RuntimeError, 'schema mismatch'):
            self.migrate(AFTER)
        self.assertEqual(self.snapshot(), expected)
