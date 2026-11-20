"""Additive upgrade and rollback preserve existing offers and invitations."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class DepositMigrationTests(TransactionTestCase):
    before = [
        ('employers', '0008_harmonize_model_names'),
        ('invitations', '0003_harmonize_model_names'),
    ]
    after = [
        ('employers', '0009_joboffer_employer_contact_and_more'),
        ('invitations', '0004_invitation_company'),
    ]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_rows_survive_upgrade_and_rollback(self):
        apps = self.migrate(self.before)
        user = apps.get_model('users', 'User').objects.create(
            email='migration-adviser@sample.example', kind='adviser', password='!'
        )
        company = apps.get_model('employers', 'Company').objects.create(
            name='Preserved establishment'
        )
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            company=company,
            created_by=user,
            email='contact@sample.example',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': 'Preserved offer'},
        )
        invitation = apps.get_model('invitations', 'Invitation').objects.create(
            sender=user, email='invited@sample.example'
        )
        apps = self.migrate(self.after)
        upgraded = apps.get_model('employers', 'JobOffer').objects.get(pk=offer.pk)
        self.assertEqual(upgraded.data, {'title': 'Preserved offer'})
        self.assertIsNone(upgraded.phone_recorded_by_id)
        self.assertIsNone(upgraded.phone_confirmed_on)
        self.assertIsNone(
            apps.get_model('invitations', 'Invitation')
            .objects.get(pk=invitation.pk)
            .company_id
        )
        apps = self.migrate(self.before)
        self.assertEqual(
            apps.get_model('employers', 'JobOffer').objects.get(pk=offer.pk).company_id,
            company.pk,
        )
        self.assertEqual(
            apps.get_model('invitations', 'Invitation')
            .objects.get(pk=invitation.pk)
            .email,
            invitation.email,
        )
