"""Retire empty legacy tables without touching current business records."""

from django.apps import apps as current_apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

BEFORE = ('employers', '0006_joboffer_structured_requirements')
AFTER = ('employers', '0007_remove_retired_employer_models')
RETIRED = ('EmployerSearchEvent', 'EmployerSearchOperation', 'EmployerEmailLink')


class RetiredModelsMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        if AFTER not in executor.loader.applied_migrations:
            historical = executor.loader.project_state([BEFORE]).apps
            for name in RETIRED:
                historical.get_model('employers', name).objects.all().delete()
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def fixture(self):
        historical = self.migrate(BEFORE)
        user = historical.get_model('users', 'User').objects.create(
            email='owner@example.invalid', kind='employer', password='!'
        )
        offer = historical.get_model('employers', 'JobOffer').objects.create(
            created_by=user,
            session_key='fictional',
            email=user.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': 'Preserved offer'},
            search_started_at=timezone.now(),
        )
        return historical, user, offer

    def test_empty_tables_removed_current_offer_and_owner_preserved_and_rollback(self):
        historical, user, offer = self.fixture()
        expected = (
            historical.get_model('employers', 'JobOffer')
            .objects.values()
            .get(pk=offer.pk)
        )
        tables = [
            historical.get_model('employers', name)._meta.db_table for name in RETIRED
        ]
        after = self.migrate(AFTER)
        self.assertTrue(
            after.get_model('users', 'User').objects.filter(pk=user.pk).exists()
        )
        self.assertEqual(
            after.get_model('employers', 'JobOffer').objects.values().get(pk=offer.pk),
            expected,
        )
        self.assertTrue(
            all(table not in connection.introspection.table_names() for table in tables)
        )
        for name in RETIRED:
            with self.assertRaises(LookupError):
                current_apps.get_model('employers', name)
        rolled_back = self.migrate(BEFORE)
        for name in RETIRED:
            self.assertEqual(
                rolled_back.get_model('employers', name).objects.count(), 0
            )
        self.migrate(AFTER)

    def test_each_nonempty_table_blocks_retirement_without_deleting_rows(self):
        historical, user, offer = self.fixture()
        Link = historical.get_model('employers', 'EmployerEmailLink')
        Operation = historical.get_model('employers', 'EmployerSearchOperation')
        Event = historical.get_model('employers', 'EmployerSearchEvent')
        link = Link.objects.create(
            email=user.email, digest='fictional', expires=timezone.now()
        )
        with self.assertRaisesMessage(RuntimeError, 'not empty'):
            self.migrate(AFTER)
        self.assertTrue(Link.objects.filter(pk=link.pk).exists())
        link.delete()
        operation = Operation.objects.create(
            offer=offer,
            requested_by=user,
            revision=1,
            state='started',
            scenario='fictional',
        )
        with self.assertRaisesMessage(RuntimeError, 'not empty'):
            self.migrate(AFTER)
        event = Event.objects.create(operation=operation, actor=user, state='started')
        with self.assertRaisesMessage(RuntimeError, 'not empty'):
            self.migrate(AFTER)
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())
        self.assertTrue(Operation.objects.filter(pk=operation.pk).exists())
        self.assertTrue(
            historical.get_model('employers', 'JobOffer')
            .objects.filter(pk=offer.pk)
            .exists()
        )
