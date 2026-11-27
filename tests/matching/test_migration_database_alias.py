"""A migration must never read or modify a different database."""

from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock


class LifecycleMigrationDatabaseTests(TestCase):
    def setUp(self):
        self.apps = Mock()
        self.editor = SimpleNamespace(connection=SimpleNamespace(alias='upgrade'))
        self.plan = self.apps.get_model.return_value
        self.query = self.plan.objects.using.return_value

    def test_backfill_reads_and_writes_the_migration_database(self):
        migration = import_module(
            'eures_beta.matching.migrations.0028_followup_matching'
        )
        row = SimpleNamespace(pk=7, review=SimpleNamespace(match_id=13))
        self.query.select_related.return_value.all.return_value.iterator.return_value = [
            row
        ]
        migration.attach(self.apps, self.editor)
        self.plan.objects.using.assert_called_once_with('upgrade')
        self.query.filter.assert_called_once_with(pk=7)
        self.query.filter.return_value.update.assert_called_once_with(match_id=13)
        self.plan.objects.filter.assert_not_called()

    def test_rollback_guards_use_the_migration_database(self):
        for module, function in (
            ('0028_followup_matching', 'check_rollback'),
            ('0031_alter_introductionfollowup_review', 'preserve_lifecycle_records'),
        ):
            with self.subTest(module=module):
                self.plan.reset_mock()
                self.query.filter.return_value.exists.return_value = False
                self.query.exists.return_value = False
                migration = import_module('eures_beta.matching.migrations.' + module)
                getattr(migration, function)(self.apps, self.editor)
                self.assertTrue(self.plan.objects.using.called)
                for call in self.plan.objects.using.call_args_list:
                    self.assertEqual(call.args, ('upgrade',))
                self.plan.objects.filter.assert_not_called()
                self.plan.objects.exists.assert_not_called()
