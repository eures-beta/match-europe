from io import StringIO
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from eures_beta.users.permissions import ACCOUNT_ADMIN_GROUP

User = get_user_model()


class VersionedPermissionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        self.adviser = User.objects.create_user(
            'adviser@example.invalid', kind='adviser'
        )
        self.employer = User.objects.create_user(
            'employer@example.invalid', kind='employer', is_staff=True
        )
        self.inactive = User.objects.create_user(
            'inactive@example.invalid', kind='adviser', is_staff=True, is_active=False
        )

    def sync(self):
        call_command('sync_group_and_perms', stdout=StringIO())

    def permission(self, action):
        return Permission.objects.get(
            content_type__app_label='users',
            content_type__model='user',
            codename=f'{action}_user',
        )

    def test_exact_policy_and_membership_are_idempotent_and_leave_flags_unchanged(self):
        self.sync()
        group = Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
        identity = group.pk
        self.assertEqual(
            set(group.permissions.values_list('codename', flat=True)),
            {'add_user', 'view_user'},
        )
        self.assertEqual(
            list(group.user_set.values_list('pk', flat=True)), [self.staff.pk]
        )
        self.sync()
        self.assertEqual(Group.objects.get(name=ACCOUNT_ADMIN_GROUP).pk, identity)
        user = User.objects.get(pk=self.staff.pk)
        self.assertTrue(user.has_perm('users.add_user'))
        self.assertTrue(user.has_perm('users.view_user'))
        self.assertFalse(user.has_perm('users.change_user'))
        self.assertFalse(user.has_perm('users.delete_user'))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.has_usable_password())
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.kind, 'employer')
        self.assertTrue(self.employer.is_staff)

    def test_drift_direct_grants_and_unmanaged_admin_grants_are_removed(self):
        self.sync()
        group = Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
        group.permissions.set([self.permission('change')])
        group.user_set.add(self.adviser, self.employer)
        rogue = Group.objects.create(name='unversioned-test-group')
        rogue.permissions.add(self.permission('delete'))
        self.adviser.groups.add(rogue)
        self.adviser.user_permissions.add(self.permission('add'))
        unrelated = Permission.objects.get(
            content_type__app_label='employers', codename='view_employerimport'
        )
        rogue.permissions.add(unrelated)
        self.adviser.user_permissions.add(unrelated)
        self.sync()
        self.assertEqual(
            set(group.permissions.values_list('codename', flat=True)),
            {'add_user', 'view_user'},
        )
        self.assertEqual(
            list(group.user_set.values_list('pk', flat=True)), [self.staff.pk]
        )
        self.assertEqual(set(rogue.permissions.all()), {unrelated})
        self.assertEqual(set(self.adviser.user_permissions.all()), {unrelated})
        self.assertTrue(self.adviser.groups.filter(pk=rogue.pk).exists())

    def test_revoked_staff_status_removes_managed_membership(self):
        self.sync()
        self.staff.is_staff = False
        self.staff.save(update_fields=['is_staff'])
        self.sync()
        self.assertFalse(User.objects.get(pk=self.staff.pk).has_perm('users.add_user'))

    def test_missing_permission_aborts_without_applying_a_partial_policy(self):
        self.sync()
        group = Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
        self.permission('view').delete()
        before = set(group.permissions.values_list('pk', flat=True))
        with self.assertRaises(CommandError):
            self.sync()
        self.assertEqual(set(group.permissions.values_list('pk', flat=True)), before)
        self.assertTrue(group.user_set.filter(pk=self.staff.pk).exists())

    def test_permission_resolution_includes_the_app_and_model(self):
        other_type = ContentType.objects.create(app_label='unrelated', model='user')
        other_permission = Permission.objects.create(
            content_type=other_type,
            codename='add_user',
            name='Fictional unrelated permission',
        )
        self.sync()
        self.assertFalse(
            Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
            .permissions.filter(pk=other_permission.pk)
            .exists()
        )

    def test_full_migrate_reapplies_policy_but_readonly_options_do_not(self):
        self.sync()
        group = Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
        group.permissions.clear()
        call_command('migrate', interactive=False, verbosity=0, stdout=StringIO())
        self.assertEqual(group.permissions.count(), 2)
        with patch('eures_beta.users.management.commands.migrate.call_command') as sync:
            call_command(
                'migrate', plan=True, interactive=False, verbosity=0, stdout=StringIO()
            )
            call_command(
                'migrate',
                check_unapplied=True,
                interactive=False,
                verbosity=0,
                stdout=StringIO(),
            )
        sync.assert_not_called()


class AccountAdministrationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            'manager@example.invalid', kind='adviser', is_staff=True
        )
        self.adviser = User.objects.create_user(
            'adviser@example.invalid', kind='adviser'
        )
        self.employer = User.objects.create_user(
            'private-employer@example.invalid', kind='employer', is_staff=True
        )
        call_command('sync_group_and_perms', stdout=StringIO())
        self.client.force_login(self.manager)

    def test_manager_can_create_only_an_ordinary_adviser_despite_forged_fields(self):
        group = Group.objects.get(name=ACCOUNT_ADMIN_GROUP)
        permission = group.permissions.first()
        response = self.client.post(
            reverse('admin:users_user_add'),
            {
                'email': 'new-adviser@example.invalid',
                'first_name': 'Fictional',
                'last_name': 'Adviser',
                'kind': 'employer',
                'is_staff': 'on',
                'is_superuser': 'on',
                'groups': [group.pk],
                'user_permissions': [permission.pk],
                'usable_password': 'true',
                'password1': 'fictional-password',
                'password2': 'fictional-password',
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new-adviser@example.invalid')
        self.assertEqual(user.kind, 'adviser')
        self.assertEqual(user.first_name, 'Fictional')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())

    def test_add_form_has_no_role_privilege_or_password_controls(self):
        response = self.client.get(reverse('admin:users_user_add'))
        self.assertEqual(response.status_code, 200)
        fields = set(response.context['adminform'].form.fields)
        self.assertEqual(fields, {'email', 'first_name', 'last_name'})

    def test_ordinary_adviser_and_staff_employer_cannot_add_users(self):
        for user in (self.adviser, self.employer):
            self.client.force_login(user)
            response = self.client.post(
                reverse('admin:users_user_add'), {'email': 'blocked@example.invalid'}
            )
            self.assertIn(response.status_code, (302, 403))
        self.assertFalse(User.objects.filter(email='blocked@example.invalid').exists())

    def test_adviser_listing_does_not_expose_employer_accounts(self):
        response = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.adviser.email)
        self.assertNotContains(response, self.employer.email)

    def test_existing_accounts_cannot_be_modified_deleted_or_promoted(self):
        response = self.client.get(
            reverse('admin:users_user_change', args=[self.adviser.pk])
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse('admin:users_user_change', args=[self.adviser.pk]),
            {
                'email': self.adviser.email,
                'is_staff': 'on',
                'is_superuser': 'on',
            },
        )
        self.assertEqual(response.status_code, 403)
        self.adviser.refresh_from_db()
        self.assertFalse(self.adviser.is_staff)
        self.assertFalse(self.adviser.is_superuser)
        self.assertEqual(
            self.client.post(
                reverse('admin:users_user_delete', args=[self.adviser.pk]),
                {'post': 'yes'},
            ).status_code,
            403,
        )
        self.assertTrue(User.objects.filter(pk=self.adviser.pk).exists())
        self.assertFalse(admin.site.is_registered(Group))

    def test_duplicate_email_is_rejected_without_a_second_account(self):
        response = self.client.post(
            reverse('admin:users_user_add'), {'email': self.adviser.email.upper()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            User.objects.filter(email__iexact=self.adviser.email).count(), 1
        )
