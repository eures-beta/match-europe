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


class EmployerAccountOwnershipMigrationTests(TransactionTestCase):
    before = [
        ('employers', '0009_joboffer_employer_contact_and_more'),
        ('invitations', '0005_remove_invitation_company'),
    ]
    after = [
        ('employers', '0010_remove_joboffer_email_and_more'),
        ('invitations', '0005_remove_invitation_company'),
    ]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_upgrade_and_rollback_preserve_offer_owner_contact_and_attribution(self):
        apps = self.migrate(self.before)
        User = apps.get_model('users', 'User')
        adviser = User.objects.create(
            email='migration-adviser@sample.example', kind='adviser', password='!'
        )
        owner = User.objects.create(
            email='owner@sample.example', kind='employer', password='!'
        )
        Offer = apps.get_model('employers', 'JobOffer')
        data = {'title': 'Preserved offer', 'companyName': 'Text only'}
        offer = Offer.objects.create(
            created_by=owner,
            email=owner.email,
            contact={'email': owner.email, 'name': 'Contact'},
            data=data,
            source_kind='manual',
            preparation_agreed_at=timezone.now(),
        )
        deposited = Offer.objects.create(
            created_by=adviser,
            phone_recorded_by=adviser,
            email='new@sample.example',
            contact={'email': 'new@sample.example', 'name': 'New contact'},
            data=data,
            source_kind='manual',
            preparation_agreed_at=timezone.now(),
        )
        apps = self.migrate(self.after)
        Offer = apps.get_model('employers', 'JobOffer')
        upgraded = Offer.objects.get(pk=offer.pk)
        self.assertEqual(upgraded.created_by_id, owner.pk)
        self.assertEqual(upgraded.contact, {'name': 'Contact'})
        self.assertEqual(upgraded.data, data)
        self.assertNotIn('email', [f.name for f in Offer._meta.fields])
        upgraded_deposit = Offer.objects.get(pk=deposited.pk)
        self.assertEqual(upgraded_deposit.adviser_id, adviser.pk)
        employer = apps.get_model('users', 'User').objects.get(
            pk=upgraded_deposit.created_by_id
        )
        self.assertEqual(employer.email, 'new@sample.example')
        self.assertEqual(employer.kind, 'employer')
        self.assertTrue(employer.is_active)
        self.assertFalse(employer.is_staff or employer.is_superuser)
        apps = self.migrate(self.before)
        restored = apps.get_model('employers', 'JobOffer').objects.get(pk=offer.pk)
        self.assertEqual(restored.email, owner.email)
        self.assertEqual(restored.contact, {'name': 'Contact', 'email': owner.email})
        self.assertEqual(restored.data, data)
        self.assertEqual(restored.created_by_id, owner.pk)

    def test_conflicting_historical_contact_blocks_without_losing_data(self):
        apps = self.migrate(self.before)
        owner = apps.get_model('users', 'User').objects.create(
            email='owner@sample.example', kind='employer', password='!'
        )
        Offer = apps.get_model('employers', 'JobOffer')
        offer = Offer.objects.create(
            created_by=owner,
            email=owner.email,
            contact={'email': 'different@sample.example'},
            source_kind='manual',
            preparation_agreed_at=timezone.now(),
        )
        with self.assertRaisesRegex(RuntimeError, 'Conflicting employer emails'):
            self.migrate(self.after)
        offer.refresh_from_db()
        self.assertEqual(offer.contact, {'email': 'different@sample.example'})
        self.assertEqual(offer.created_by_id, owner.pk)
        offer.contact = {'email': owner.email}
        offer.save()

    def test_database_rejects_wrong_owner_role_and_email_copy(self):
        from django.db import IntegrityError, transaction
        from eures_beta.users.models import User
        from eures_beta.employers.models import JobOffer

        adviser = User.objects.create_user(
            'adviser-role@sample.example', kind='adviser'
        )
        owner = User.objects.create_user(
            'employer-role@sample.example', kind='employer'
        )
        offer = JobOffer.objects.create(
            created_by=owner,
            adviser=adviser,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
        )
        for changes in (
            {'created_by': adviser},
            {'adviser': owner},
            {'contact': {'email': owner.email}},
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                JobOffer.objects.filter(pk=offer.pk).update(**changes)
