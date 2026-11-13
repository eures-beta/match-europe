"""Existing invitations, accepted accounts and permission grants survive renaming."""

from django.core import signing
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class InvitationNamesMigrationTests(TransactionTestCase):
    before = ('users', '0007_user_adviser_organisation')
    after = ('users', '0008_invitation_names')

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_populated_upgrade_and_reverse_preserve_data_and_old_token(self):
        apps = self.migrate(self.before)
        User = apps.get_model('users', 'User')
        OldInvitation = apps.get_model('users', 'EmployerInvitation')
        sender = User.objects.create(
            email='sender@example.invalid',
            kind='adviser',
            password='!',
            adviser_organisation='Fictional organization',
        )
        snapshots = []
        accepted_at = timezone.now()
        for kind in ('employer', 'candidate', 'adviser'):
            recipient = User.objects.create(
                email=f'accepted-{kind}@example.invalid',
                kind=kind,
                password='!',
            )
            row = OldInvitation.objects.create(
                email=recipient.email,
                invited_by=sender,
                audience=kind,
                first_name='Fictional',
                last_name='Recipient',
                employer=recipient,
                accepted_at=accepted_at,
                email_sent_at=accepted_at,
                reminder_sent_at=accepted_at,
            )
            snapshots.append(
                (row.pk, row.nonce, row.created_at, row.expires_at, kind, recipient.pk)
            )
        pending = OldInvitation.objects.create(
            email='pending@example.invalid',
            invited_by=sender,
        )
        token = signing.dumps(
            {'id': str(pending.pk), 'nonce': str(pending.nonce)},
            salt='users.employer-invitation.v1',
        )
        ContentType = apps.get_model('contenttypes', 'ContentType')
        content_type, _ = ContentType.objects.get_or_create(
            app_label='users',
            model='employerinvitation',
        )
        Permission = apps.get_model('auth', 'Permission')
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_employerinvitation',
            defaults={'name': 'Can view employer invitation'},
        )
        Group = apps.get_model('auth', 'Group')
        group = Group.objects.create(name='migration-test-inviters')
        group.permissions.add(permission)

        self.migrate(self.after)
        from eures_beta.users.models import Invitation, User as CurrentUser
        from eures_beta.users.invitations import find_invitation
        from django.contrib.auth.models import Permission as CurrentPermission

        for pk, nonce, created, expires, kind, recipient_pk in snapshots:
            row = Invitation.objects.get(pk=pk)
            self.assertEqual(
                (
                    row.nonce,
                    row.created_at,
                    row.expires_at,
                    row.recipient_kind,
                    row.recipient_id,
                    row.sender_id,
                ),
                (nonce, created, expires, kind, recipient_pk, sender.pk),
            )
            self.assertEqual(row.recipient.invitation.pk, pk)
            self.assertEqual(row.accepted_at, accepted_at)
            self.assertEqual(row.email_sent_at, accepted_at)
            self.assertEqual(row.reminder_sent_at, accepted_at)
            self.assertEqual(
                (row.first_name, row.last_name), ('Fictional', 'Recipient')
            )
        self.assertEqual(
            CurrentUser.objects.get(pk=sender.pk).organization_name,
            'Fictional organization',
        )
        self.assertEqual(
            CurrentUser.objects.get(pk=sender.pk).sent_invitations.count(), 4
        )
        self.assertEqual(find_invitation(token).pk, pending.pk)
        renamed = CurrentPermission.objects.get(pk=permission.pk)
        self.assertEqual(renamed.codename, 'view_invitation')
        self.assertTrue(renamed.group_set.filter(pk=group.pk).exists())

        apps = self.migrate(self.before)
        self.assertEqual(
            apps.get_model('users', 'EmployerInvitation').objects.count(), 4
        )
        restored = apps.get_model('users', 'User').objects.get(pk=sender.pk)
        self.assertEqual(restored.adviser_organisation, 'Fictional organization')
        self.assertEqual(
            apps.get_model('auth', 'Permission').objects.get(pk=permission.pk).codename,
            'view_employerinvitation',
        )
