"""Moving an app preserves existing invitations, links and permission identities."""

from io import StringIO
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class InvitationAppMigrationTests(TransactionTestCase):
    before = ('users', '0008_invitation_names')
    after = ('users', '0009_move_invitation_to_own_app')

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def table_identity(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 'users_invitation'::regclass::oid")
            return cursor.fetchone()[0]

    def test_populated_move_and_reverse_keep_data_links_and_grants(self):
        old = self.migrate(self.before)
        User = old.get_model('users', 'User')
        Invitation = old.get_model('users', 'Invitation')
        sender = User.objects.create(
            email='sender@example.invalid', kind='adviser', password='!'
        )
        snapshots = []
        for kind in ('candidate', 'employer', 'adviser'):
            recipient = User.objects.create(
                email=f'{kind}@example.invalid', kind=kind, password='!'
            )
            row = Invitation.objects.create(
                email=recipient.email,
                sender=sender,
                recipient=recipient,
                recipient_kind=kind,
                first_name='Fictional',
                last_name='Recipient',
                language='de',
                accepted_at=timezone.now(),
                email_sent_at=timezone.now(),
                reminder_sent_at=timezone.now(),
            )
            snapshots.append(Invitation.objects.values().get(pk=row.pk))
        pending = Invitation.objects.create(
            email='pending@example.invalid', sender=sender
        )
        from eures_beta.invitations.services import invitation_token, find_invitation

        token = invitation_token(pending)
        CT = old.get_model('contenttypes', 'ContentType')
        content_type, _ = CT.objects.get_or_create(
            app_label='users', model='invitation'
        )
        Permission = old.get_model('auth', 'Permission')
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_invitation',
            defaults={'name': 'Can view invitation'},
        )
        Group = old.get_model('auth', 'Group')
        group = Group.objects.create(name='invitation-move-test')
        group.permissions.add(permission)
        sender.user_permissions.add(permission)
        log = LogEntry.objects.create(
            user_id=sender.pk,
            content_type_id=content_type.pk,
            object_id=str(pending.pk),
            object_repr='Fictional invitation',
            action_flag=1,
        )
        table = self.table_identity()

        new = self.migrate(self.after)
        Moved = new.get_model('invitations', 'Invitation')
        self.assertEqual(self.table_identity(), table)
        self.assertEqual(Moved.objects.count(), 4)
        for expected in snapshots:
            self.assertEqual(Moved.objects.values().get(pk=expected['id']), expected)
        with self.assertRaises(LookupError):
            new.get_model('users', 'Invitation')
        self.assertEqual(find_invitation(token).pk, pending.pk)
        self.assertEqual(
            new.get_model('users', 'User')
            .objects.get(pk=sender.pk)
            .sent_invitations.count(),
            4,
        )
        moved_type = new.get_model('contenttypes', 'ContentType').objects.get(
            pk=content_type.pk
        )
        self.assertEqual(
            (moved_type.app_label, moved_type.model), ('invitations', 'invitation')
        )
        moved_permission = new.get_model('auth', 'Permission').objects.get(
            pk=permission.pk
        )
        self.assertEqual(moved_permission.content_type_id, content_type.pk)
        self.assertTrue(moved_permission.group_set.filter(pk=group.pk).exists())
        self.assertTrue(moved_permission.user_set.filter(pk=sender.pk).exists())
        self.assertEqual(
            LogEntry.objects.get(pk=log.pk).content_type_id,
            content_type.pk,
        )
        from eures_beta.invitations.models import Invitation as CurrentInvitation
        from eures_beta.users.models import User as CurrentUser

        current_recipient = CurrentUser.objects.get(pk=snapshots[0]['recipient_id'])
        self.assertEqual(current_recipient.invitation.pk, snapshots[0]['id'])
        self.assertEqual(CurrentInvitation._meta.app_label, 'invitations')
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, 'users_invitation'
            )
        self.assertTrue(constraints['users_invitation_email_ci']['unique'])

        restored = self.migrate(self.before)
        self.assertEqual(self.table_identity(), table)
        for expected in snapshots:
            self.assertEqual(
                restored.get_model('users', 'Invitation')
                .objects.values()
                .get(pk=expected['id']),
                expected,
            )
        self.assertEqual(
            restored.get_model('contenttypes', 'ContentType')
            .objects.get(pk=content_type.pk)
            .app_label,
            'users',
        )
        self.assertEqual(find_invitation(token).pk, pending.pk)

    def test_conflicting_content_types_abort_instead_of_merging_permissions(self):
        old = self.migrate(self.before)
        CT = old.get_model('contenttypes', 'ContentType')
        CT.objects.get_or_create(app_label='users', model='invitation')
        duplicate = CT.objects.create(app_label='invitations', model='invitation')
        try:
            with self.assertRaisesMessage(
                RuntimeError, 'Conflicting invitation content types'
            ):
                self.migrate(self.after)
        finally:
            CT.objects.filter(pk=duplicate.pk).delete()

    def test_app_targeted_migrate_finishes_transfer_before_creating_permissions(self):
        old = self.migrate(self.before)
        User = old.get_model('users', 'User')
        sender = User.objects.create(
            email='targeted-sender@example.invalid', kind='adviser', password='!'
        )
        invitation = old.get_model('users', 'Invitation').objects.create(
            email='targeted-recipient@example.invalid', sender=sender
        )
        table = self.table_identity()
        call_command(
            'migrate', 'invitations', interactive=False, verbosity=0, stdout=StringIO()
        )
        from eures_beta.invitations.models import Invitation

        self.assertEqual(self.table_identity(), table)
        self.assertEqual(Invitation.objects.get(pk=invitation.pk).sender_id, sender.pk)
        self.assertFalse(
            ContentType.objects.filter(app_label='users', model='invitation').exists()
        )
        self.assertEqual(
            ContentType.objects.filter(
                app_label='invitations', model='invitation'
            ).count(),
            1,
        )
