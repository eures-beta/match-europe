"""An existing response profile survives upgrade and rollback, including grants."""

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = ('employers', '0004_employerresponsepractice')
AFTER = ('employers', '0005_employer_profile')


class ProfileRenameMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        ContentType.objects.clear_cache()
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def test_existing_profile_and_admin_metadata_survive_both_directions(self):
        apps = self.migrate(BEFORE)
        User = apps.get_model('users', 'User')
        user = User.objects.create(
            email='profile-owner@example.invalid', kind='employer', password='!'
        )
        original = apps.get_model(
            'employers', 'EmployerResponsePractice'
        ).objects.create(
            employer_id=user.pk,
            response_coverage='selected',
            response_time='two_weeks_month',
            revision=4,
        )
        snapshot = (
            original.response_coverage,
            original.response_time,
            original.revision,
            original.created,
            original.updated,
        )
        CT = apps.get_model('contenttypes', 'ContentType')
        content_type, _ = CT.objects.get_or_create(
            app_label='employers', model='employerresponsepractice'
        )
        Permission = apps.get_model('auth', 'Permission')
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_employerresponsepractice',
            defaults={'name': 'Can view employer response practice'},
        )
        group = apps.get_model('auth', 'Group').objects.create(name='profile-readers')
        group.permissions.add(permission)
        user.user_permissions.add(permission)
        log = apps.get_model('admin', 'LogEntry').objects.create(
            user_id=user.pk,
            content_type_id=content_type.pk,
            object_id=str(original.pk),
            object_repr='Fictional profile',
            action_flag=1,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT 'employers_employerresponsepractice'::regclass::oid")
            table_oid = cursor.fetchone()[0]

        for target, model, field, label in (
            (AFTER, 'EmployerProfile', 'user_id', 'employerprofile'),
            (
                BEFORE,
                'EmployerResponsePractice',
                'employer_id',
                'employerresponsepractice',
            ),
        ):
            apps = self.migrate(target)
            row = apps.get_model('employers', model).objects.get(pk=original.pk)
            self.assertEqual(getattr(row, field), user.pk)
            self.assertEqual(
                (
                    row.response_coverage,
                    row.response_time,
                    row.revision,
                    row.created,
                    row.updated,
                ),
                snapshot,
            )
            with connection.cursor() as cursor:
                cursor.execute('SELECT %s::regclass::oid', [row._meta.db_table])
                self.assertEqual(cursor.fetchone()[0], table_oid)
            self.assertEqual(
                apps.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .model,
                label,
            )
            self.assertEqual(
                apps.get_model('auth', 'Permission')
                .objects.get(pk=permission.pk)
                .codename,
                f'view_{label}',
            )
            self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
            self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
            self.assertEqual(
                apps.get_model('admin', 'LogEntry')
                .objects.get(pk=log.pk)
                .content_type_id,
                content_type.pk,
            )
