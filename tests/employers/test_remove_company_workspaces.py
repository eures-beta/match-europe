"""Retiring sharing keeps owned offers and refuses implicit ownership transfer."""

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

BEFORE = ('employers', '0008_harmonize_model_names')
AFTER = ('employers', '0009_remove_company_workspaces')


class RemoveCompanyWorkspacesTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        ContentType.objects.clear_cache()
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        if AFTER not in executor.loader.applied_migrations:
            apps = executor.loader.project_state([BEFORE]).apps
            apps.get_model('employers', 'JobOffer').objects.filter(
                company__isnull=False
            ).update(company=None)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def fixture(self, owned=True):
        apps = self.migrate(BEFORE)
        user = apps.get_model('users', 'User').objects.create(
            email='owner@example.invalid', kind='employer', password='!'
        )
        company = apps.get_model('employers', 'Company').objects.create(
            name='Fictional establishment'
        )
        apps.get_model('employers', 'CompanyMembership').objects.create(
            company=company, user=user
        )
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            company=company,
            created_by=user if owned else None,
            email='contact@example.invalid',
            session_key='',
            preparation_agreed_at=timezone.now(),
            source_kind='pdf',
            contact={'name': 'Contact'},
            data={
                'title': 'Preserved offer',
                'companyName': 'Preserved displayed name',
                'description': 'Extracted text',
            },
            revision=3,
        )
        return apps, user, offer

    def test_populated_upgrade_preserves_offer_owner_data_and_identifiers(self):
        apps, user, offer = self.fixture()
        unlinked = apps.get_model('employers', 'JobOffer').objects.create(
            created_by=user,
            email=user.email,
            session_key='',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': 'Already personal'},
        )
        before = list(
            apps.get_model('employers', 'JobOffer').objects.order_by('pk').values()
        )
        for row in before:
            row.pop('company_id')
        ct, _ = apps.get_model('contenttypes', 'ContentType').objects.get_or_create(
            app_label='employers', model='company'
        )
        permission, _ = apps.get_model('auth', 'Permission').objects.get_or_create(
            content_type=ct,
            codename='view_company',
            defaults={'name': 'Retired permission'},
        )
        user.user_permissions.add(permission)
        apps = self.migrate(AFTER)
        self.assertEqual(
            list(
                apps.get_model('employers', 'JobOffer').objects.order_by('pk').values()
            ),
            before,
        )
        tables = connection.introspection.table_names()
        self.assertNotIn('employers_company', tables)
        self.assertNotIn('employers_companymembership', tables)
        self.assertFalse(
            apps.get_model('auth', 'Permission')
            .objects.filter(pk=permission.pk)
            .exists()
        )
        self.assertTrue(
            apps.get_model('users', 'User').objects.filter(pk=user.pk).exists()
        )
        for name in ('Company', 'CompanyMembership'):
            with self.assertRaises(LookupError):
                apps.get_model('employers', name)
        # Reverse recreates an empty schema, never pretends to recover discarded sharing data.
        apps = self.migrate(BEFORE)
        self.assertEqual(apps.get_model('employers', 'Company').objects.count(), 0)
        self.assertEqual(apps.get_model('employers', 'JobOffer').objects.count(), 2)
        self.migrate(AFTER)

    def test_attached_offer_without_owner_blocks_before_any_drop(self):
        apps, _, offer = self.fixture(owned=False)
        with self.assertRaisesMessage(RuntimeError, 'explicit employer owner'):
            self.migrate(AFTER)
        self.assertIn('employers_company', connection.introspection.table_names())
        self.assertIsNotNone(
            apps.get_model('employers', 'JobOffer').objects.get(pk=offer.pk).company_id
        )
