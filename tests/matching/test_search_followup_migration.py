from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class SearchFollowUpMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        targets = [('matching', name)]
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_naming_roundtrip_preserves_the_search_and_foreign_keys(self):
        apps = self.migrate('0012_advisersearchfollowup')
        User = apps.get_model('users', 'User')
        employer = User.objects.create(
            email='employer@migration.invalid', kind='employer'
        )
        adviser = User.objects.create(email='adviser@migration.invalid', kind='adviser')
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            created_by=employer,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            email=employer.email,
            data={'title': 'Fictional migration offer'},
        )
        row = apps.get_model('matching', 'AdviserSearchFollowUp').objects.create(
            offer=offer,
            updated_by=adviser,
            searching=True,
            follow_up_on=date(2026, 11, 20),
        )
        for name in (
            '0013_search_followup_database_names',
            '0012_advisersearchfollowup',
            '0013_search_followup_database_names',
        ):
            apps = self.migrate(name)
            current = apps.get_model('matching', 'AdviserSearchFollowUp').objects.get(
                pk=row.pk
            )
            self.assertEqual(current.offer_id, offer.pk)
            self.assertEqual(current.updated_by_id, adviser.pk)
            self.assertEqual(current.follow_up_on, row.follow_up_on)
            self.assertTrue(current.searching)
