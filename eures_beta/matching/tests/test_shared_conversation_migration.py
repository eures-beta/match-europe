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
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class SharedConversationMigrationTests(TransactionTestCase):
    def test_complete_rename_preserves_rows_schema_objects_and_permissions(self):
        fixture = self.prepare()
        apps = self.migrate(AFTER)
        conversation = apps.get_model('matching', 'SharedConversation')
        message = apps.get_model('matching', 'SharedMessage')
        thread_id, message_id = self.populate(conversation, message, fixture)
        expected = list(self.snapshot().values())
        content_type, _ = apps.get_model(
            'contenttypes', 'ContentType'
        ).objects.get_or_create(app_label='matching', model='sharedconversation')
        permission, _ = apps.get_model('auth', 'Permission').objects.get_or_create(
            content_type_id=content_type.pk,
            codename='view_sharedconversation',
            defaults={'name': 'Can view shared conversation'},
        )
        group = apps.get_model('auth', 'Group').objects.create(name='Migration fixture')
        group.permissions.add(permission)
        before_objects = self.schema_objects(
            'matching_sharedconversation', 'matching_sharedmessage'
        )
        apps = self.migrate('0009_candidate_offer_conversation_names')
        conversation = apps.get_model('matching', 'CandidateOfferConversation')
        message = apps.get_model('matching', 'CandidateOfferConversationMessage')
        self.assertEqual(
            conversation.objects.get(pk=thread_id).offer_review_id, fixture[1]
        )
        self.assertEqual(message.objects.get(pk=message_id).conversation_id, thread_id)
        self.assertEqual(
            conversation._meta.get_field('offer_review').remote_field.related_name,
            'candidate_offer_conversation',
        )
        new_tables = (
            'matching_candidateofferconversation',
            'matching_candidateofferconversationmessage',
        )
        with connection.cursor() as cursor:
            for table, (old_oid, old_rows) in zip(new_tables, expected):
                cursor.execute('SELECT %s::regclass::oid', [table])
                self.assertEqual(cursor.fetchone()[0], old_oid)
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                self.assertEqual(cursor.fetchall(), old_rows)
            for table in new_tables:
                columns = connection.introspection.get_table_description(cursor, table)
                self.assertNotIn('confirmation_id', [c.name for c in columns])
        objects = self.schema_objects(*new_tables)
        # Django rebuilds affected foreign-key constraints during RenameField;
        # rows, table identities and sequence identities must survive.
        self.assertEqual(len(objects), len(before_objects))
        self.assertEqual(
            {oid for oid, name in objects.items() if name.endswith('_id_seq')},
            {oid for oid, name in before_objects.items() if name.endswith('_id_seq')},
        )
        self.assertTrue(
            all(
                'sharedconversation' not in n
                and 'sharedmessage' not in n
                and 'confirmation' not in n
                for n in objects.values()
            ),
            objects,
        )
        self.assertNotIn(
            'matching_sharedconversation', connection.introspection.table_names()
        )
        self.assertNotIn(
            'matching_sharedmessage', connection.introspection.table_names()
        )
        self.assertEqual(
            apps.get_model('contenttypes', 'ContentType')
            .objects.get(pk=content_type.pk)
            .model,
            'candidateofferconversation',
        )
        self.assertEqual(
            apps.get_model('auth', 'Permission').objects.get(pk=permission.pk).codename,
            'view_candidateofferconversation',
        )
        self.assertEqual(
            list(
                apps.get_model('auth', 'Group')
                .objects.get(pk=group.pk)
                .permissions.values_list('pk', flat=True)
            ),
            [permission.pk],
        )
        later = message.objects.create(
            conversation_id=thread_id, author_id=fixture[3], body='Next fictional reply'
        )
        self.assertGreater(later.pk, message_id)
        later.delete()
        apps = self.migrate(AFTER)
        self.assertEqual(list(self.snapshot().values()), expected)
        self.assertEqual(
            apps.get_model('auth', 'Permission').objects.get(pk=permission.pk).codename,
            'view_sharedconversation',
        )
        self.assertEqual(
            apps.get_model('contenttypes', 'ContentType')
            .objects.get(pk=content_type.pk)
            .model,
            'sharedconversation',
        )
        self.migrate('0009_candidate_offer_conversation_names')
        self.assertEqual(len(self.schema_objects(*new_tables)), len(before_objects))

    def schema_objects(self, *tables):
        result = {}
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(
                    'SELECT oid, conname FROM pg_constraint WHERE conrelid=%s::regclass',
                    [table],
                )
                result.update(cursor.fetchall())
                cursor.execute(
                    'SELECT c.oid, c.relname FROM pg_class c WHERE c.oid IN '
                    '(SELECT indexrelid FROM pg_index WHERE indrelid=%s::regclass) '
                    'OR c.oid=pg_get_serial_sequence(%s, %s)::regclass',
                    [table, table, 'id'],
                )
                result.update(cursor.fetchall())
        return result

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
