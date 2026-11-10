"""Renaming matching models must preserve rows, references and granted rights."""

from io import StringIO

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext


@override_settings(
    MATCHING_LOCAL_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    SHARED_DEMO=False,
)
class MatchModelRenameTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        ContentType.objects.clear_cache()
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def snapshot(self):
        result = {}
        with connection.cursor() as cursor:
            for name in ('matchpair', 'evaluation', 'decision', 'offerrequirements'):
                table = 'matching_' + name
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                result[table] = (oid, cursor.fetchall())
        return result

    def assert_rename_preserves_data(self, before, after, old, new):
        apps = self.migrate(before)
        call_command('seed_matching_trial', stdout=StringIO())
        evaluation_name = 'MatchEvaluation' if old == 'Decision' else old
        evaluation = apps.get_model('matching', evaluation_name).objects.first()
        apps.get_model('matching', 'Decision').objects.create(
            pair_id=evaluation.pair_id,
            evaluation_id=evaluation.pk,
            value='retained',
        )
        content_type, _ = ContentType.objects.get_or_create(
            app_label='matching', model=old.lower()
        )
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_' + old.lower(),
            defaults={'name': 'Fictional observer'},
        )
        group = Group.objects.create(name='fictional-matching-observers')
        group.permissions.add(permission)
        snapshot = self.snapshot()
        with CaptureQueriesContext(connection) as queries:
            apps = self.migrate(after)
        self.assertFalse(
            any(
                query['sql'].lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP '))
                for query in queries
            )
        )
        self.assertEqual(self.snapshot(), snapshot)
        self.assertTrue(apps.get_model('matching', new).objects.exists())
        content_type.refresh_from_db()
        permission.refresh_from_db()
        self.assertEqual(content_type.model, new.lower())
        self.assertEqual(permission.codename, 'view_' + new.lower())
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
        self.migrate(before)
        self.assertEqual(self.snapshot(), snapshot)
        content_type.refresh_from_db()
        permission.refresh_from_db()
        self.assertEqual(content_type.model, old.lower())
        self.assertEqual(permission.codename, 'view_' + old.lower())
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())

    def test_evaluation_rename_and_rollback_preserve_data(self):
        self.assert_rename_preserves_data(
            '0001_initial',
            '0002_rename_match_evaluation',
            'Evaluation',
            'MatchEvaluation',
        )

    def test_decision_rename_and_rollback_preserve_data(self):
        self.assert_rename_preserves_data(
            '0002_rename_match_evaluation',
            '0003_rename_match_decision',
            'Decision',
            'MatchDecision',
        )
