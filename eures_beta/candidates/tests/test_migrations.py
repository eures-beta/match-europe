from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CandidateProfileMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        executor = MigrationExecutor(connection)
        return executor.loader.project_state(
            list(executor.loader.applied_migrations)
        ).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_add_and_reverse_empty_table_preserves_accounts(self):
        apps = self.migrate(('candidates', None))
        User = apps.get_model('users', 'User')
        account = User.objects.create(
            email='migration@example.test', kind='candidate', password='!'
        )
        original = list(User.objects.filter(pk=account.pk).values())
        apps = self.migrate(('candidates', '0001_initial'))
        Profile = apps.get_model('candidates', 'CandidateProfile')
        self.assertEqual(Profile.objects.count(), 0)
        self.assertEqual(list(User.objects.filter(pk=account.pk).values()), original)
        employer = User.objects.create(
            email='employer-migration@example.test', kind='employer', password='!'
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.create(user_id=employer.pk)
        self.migrate(('candidates', None))
        self.assertNotIn(
            'candidates_candidateprofile', connection.introspection.table_names()
        )
        self.assertEqual(list(User.objects.filter(pk=account.pk).values()), original)
