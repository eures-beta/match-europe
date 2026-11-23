"""A cross-app move must preserve the suggestions, physical objects and rights."""

from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile

BEFORE = [
    ('matching', '0020_candidate_offer_review_event'),
    ('candidates', '0009_harmonize_model_names'),
]
AFTER = [
    ('matching', '0021_move_profile_review_suggestion'),
    ('candidates', '0010_move_profile_review_suggestion'),
]


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class ProfileReviewSuggestionMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def physical_identity(self, model):
        table = model._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT %s::regclass::oid, pg_get_serial_sequence(%s, %s)::regclass::oid',
                [table, table, 'id'],
            )
            table_oid, sequence_oid = cursor.fetchone()
            cursor.execute(
                'SELECT oid FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY oid',
                [table],
            )
            constraints = cursor.fetchall()
            cursor.execute(
                'SELECT indexrelid FROM pg_index WHERE indrelid=%s::regclass ORDER BY indexrelid',
                [table],
            )
            indexes = cursor.fetchall()
            cursor.execute(
                'SELECT last_value FROM pg_sequences WHERE schemaname=current_schema() AND sequencename=(SELECT relname FROM pg_class WHERE oid=%s)',
                [sequence_oid],
            )
            return table_oid, sequence_oid, constraints, indexes, cursor.fetchone()[0]

    def test_nonempty_roundtrip_preserves_pending_and_resolved_suggestions(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        profile = CandidateProfile.objects.first()
        old = self.migrate(BEFORE)
        Suggestion = old.get_model('matching', 'CandidateProfileReviewPrompt')
        data = {
            'candidate_id': profile.pk,
            'profile_updated_at': profile.updated_at,
            'condition': {'kind': 'schedule', 'expected': ['saturday']},
            'evidence': [{'offer': 'fictional-offer', 'answer': 17}],
        }
        Suggestion.objects.create(
            id=101,
            condition_hash='a' * 64,
            resolution='review',
            resolved_at=timezone.now(),
            **data,
        )
        Suggestion.objects.create(id=102, condition_hash='b' * 64, **data)
        expected = list(Suggestion.objects.order_by('pk').values())
        content_type, _ = old.get_model(
            'contenttypes', 'ContentType'
        ).objects.get_or_create(
            app_label='matching', model='candidateprofilereviewprompt'
        )
        permission, _ = old.get_model('auth', 'Permission').objects.get_or_create(
            content_type=content_type,
            codename='view_candidateprofilereviewprompt',
            defaults={'name': 'Can view candidate profile review prompt'},
        )
        group = old.get_model('auth', 'Group').objects.create(
            name='Fictional suggestion observers'
        )
        group.permissions.add(permission)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT setval(pg_get_serial_sequence(%s, %s), 333, true)',
                [Suggestion._meta.db_table, 'id'],
            )
        identity = self.physical_identity(Suggestion)

        for targets, app, name, absent in (
            (
                AFTER,
                'candidates',
                'CandidateProfileReviewSuggestion',
                'matching_candidateprofilereviewprompt',
            ),
            (
                BEFORE,
                'matching',
                'CandidateProfileReviewPrompt',
                'candidates_candidateprofilereviewsuggestion',
            ),
            (
                AFTER,
                'candidates',
                'CandidateProfileReviewSuggestion',
                'matching_candidateprofilereviewprompt',
            ),
        ):
            state = self.migrate(targets)
            Suggestion = state.get_model(app, name)
            self.assertEqual(self.physical_identity(Suggestion), identity)
            self.assertEqual(list(Suggestion.objects.order_by('pk').values()), expected)
            self.assertNotIn(absent, connection.introspection.table_names())
            current_type = state.get_model('contenttypes', 'ContentType').objects.get(
                pk=content_type.pk
            )
            self.assertEqual(
                (current_type.app_label, current_type.model), (app, name.lower())
            )
            current_permission = state.get_model('auth', 'Permission').objects.get(
                pk=permission.pk
            )
            self.assertEqual(current_permission.codename, 'view_' + name.lower())
            self.assertEqual(current_permission.content_type_id, content_type.pk)
            self.assertTrue(group.permissions.filter(pk=permission.pk).exists())

        with self.assertRaises(IntegrityError), transaction.atomic():
            Suggestion.objects.create(condition_hash='a' * 64, **data)
        added = Suggestion.objects.create(condition_hash='c' * 64, **data)
        self.assertGreater(added.pk, 333)
