"""Exercise the published schema with actual rows, grants and a round trip."""

from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PlanningMigrationTests(TransactionTestCase):
    def test_move_preserves_data_sql_identity_and_permission_grants(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        old_target = [('users', '0011_adviseravailability'), ('planning', None)]
        try:
            executor.migrate(old_target)
            old_apps = executor.loader.project_state(
                [('users', '0011_adviseravailability')]
            ).apps
            CT = old_apps.get_model('contenttypes', 'ContentType')
            CT.objects.filter(
                app_label='planning', model='staffdailyavailability'
            ).delete()
            user = old_apps.get_model('users', 'User').objects.create(
                email='migration@example.invalid', kind='employer', is_staff=True
            )
            record = old_apps.get_model('users', 'AdviserAvailability').objects.create(
                adviser_id=user.pk, day=date(2026, 11, 28), present=True
            )
            ct, _ = CT.objects.get_or_create(
                app_label='users', model='adviseravailability'
            )
            perm = old_apps.get_model('auth', 'Permission').objects.get_or_create(
                content_type=ct,
                codename='view_adviseravailability',
                defaults={'name': 'Can view adviser availability'},
            )[0]
            group = old_apps.get_model('auth', 'Group').objects.create(
                name='planning migration grant'
            )
            group.permissions.add(perm)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 'users_adviseravailability'::regclass::oid, pg_get_serial_sequence('users_adviseravailability', 'id')::regclass::oid"
                )
                original_oids = cursor.fetchone()
            for target, app, model, field in (
                (
                    [('planning', '0001_initial')],
                    'planning',
                    'StaffDailyAvailability',
                    'user',
                ),
                (old_target, 'users', 'AdviserAvailability', 'adviser'),
                (
                    [('planning', '0001_initial')],
                    'planning',
                    'StaffDailyAvailability',
                    'user',
                ),
            ):
                executor = MigrationExecutor(connection)
                executor.migrate(target)
                state_targets = [t for t in target if t[1] is not None]
                apps = executor.loader.project_state(state_targets).apps
                Model = apps.get_model(app, model)
                row = Model.objects.get(pk=record.pk)
                self.assertEqual(getattr(row, field + '_id'), user.pk)
                self.assertTrue(row.present)
                self.assertEqual(row.day, date(2026, 11, 28))
                table = Model._meta.db_table
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT %s::regclass::oid, pg_get_serial_sequence(%s, %s)::regclass::oid',
                        [table, table, 'id'],
                    )
                    self.assertEqual(cursor.fetchone(), original_oids)
                    objects = connection.introspection.get_constraints(cursor, table)
                    self.assertTrue(
                        all(name.startswith(table + '_') for name in objects)
                    )
                migrated_ct = apps.get_model('contenttypes', 'ContentType').objects.get(
                    pk=ct.pk
                )
                self.assertEqual(
                    (migrated_ct.app_label, migrated_ct.model), (app, model.lower())
                )
                self.assertEqual(
                    apps.get_model('auth', 'Permission')
                    .objects.get(pk=perm.pk)
                    .codename,
                    'view_' + model.lower(),
                )
                self.assertTrue(
                    apps.get_model('auth', 'Group')
                    .objects.get(pk=group.pk)
                    .permissions.filter(pk=perm.pk)
                    .exists()
                )
                self.assertGreater(
                    Model.objects.create(
                        **{
                            field + '_id': user.pk,
                            'day': date(2026, 11, 29),
                            'present': False,
                        }
                    ).pk,
                    record.pk,
                )
                Model.objects.filter(day=date(2026, 11, 29)).delete()
        finally:
            MigrationExecutor(connection).migrate(leaves)
