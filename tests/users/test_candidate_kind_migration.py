"""Allow candidate accounts without changing existing accounts or role guards."""

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = ('users', '0004_employerinvitation')
AFTER = ('users', '0005_candidate_kind')


class CandidateKindMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps.get_model('users', 'User')

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_upgrade_preserves_accounts_and_database_guards(self):
        User = self.migrate(BEFORE)
        for kind in ('adviser', 'employer'):
            User.objects.create(
                email=f'{kind}@example.invalid', kind=kind, password='!'
            )
        original = list(User.objects.order_by('pk').values())
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='candidate@example.invalid', kind='candidate')

        User = self.migrate(AFTER)
        self.assertEqual(list(User.objects.order_by('pk').values()), original)
        candidate = User.objects.create(
            email='candidate@example.invalid', kind='candidate', password='!'
        )
        for invalid in ('', 'admin', 'unknown'):
            with (
                self.subTest(kind=invalid),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                User.objects.create(email='invalid@example.invalid', kind=invalid)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=candidate.pk).update(kind='employer')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='CANDIDATE@example.invalid', kind='candidate')

        # Reversing the schema is possible before any candidate accounts exist.
        candidate.delete()
        User = self.migrate(BEFORE)
        self.assertEqual(list(User.objects.order_by('pk').values()), original)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='candidate@example.invalid', kind='candidate')
