from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class DomainMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_rows_relations_tables_and_permission_ids_survive_round_trip(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before = [
            (
                'journeys',
                '0014_alter_match_offer_alter_answer_question_delete_offer_and_more',
            ),
            ('accounts', None),
        ]
        try:
            old = self.migrate(before)
            user = old.get_model('auth', 'User').objects.create(
                username='accounts@example.invalid'
            )
            old.get_model('journeys', 'Profile').objects.create(
                user_id=user.pk,
                role='candidate',
                verified=True,
                name='Fictional saved profile',
            )
            old.get_model('journeys', 'AccessToken').objects.create(
                user_id=user.pk, digest='a' * 64, expires=timezone.now(), used=True
            )
            old.get_model('journeys', 'Event').objects.create(
                actor_id=user.pk,
                action='saved_event',
                object_type='profile',
                object_id=1,
            )
            snapshots = {}
            permissions = []
            for name in ['Profile', 'AccessToken', 'Event']:
                model = old.get_model('journeys', name)
                snapshots[model._meta.db_table] = list(
                    model.objects.order_by('pk').values()
                )
                ct, _ = old.get_model(
                    'contenttypes', 'ContentType'
                ).objects.get_or_create(app_label='journeys', model=name.lower())
                perm, _ = old.get_model('auth', 'Permission').objects.get_or_create(
                    content_type_id=ct.pk,
                    codename='view_' + name.lower(),
                    defaults={'name': 'Fictional permission'},
                )
                user.user_permissions.add(perm)
                permissions.append((ct.pk, perm.pk))
            if 'accounts' == 'matching':
                model = old.get_model('conversations', 'Conversation')
                snapshots[model._meta.db_table] = list(
                    model.objects.order_by('pk').values()
                )
            tables = set(connection.introspection.table_names())
            for targets, label in [(leaves, 'accounts'), (before, 'journeys')]:
                state = self.migrate(targets)
                for table, rows in snapshots.items():
                    model = next(
                        m for m in state.get_models() if m._meta.db_table == table
                    )
                    self.assertEqual(list(model.objects.order_by('pk').values()), rows)
                for ct, perm in permissions:
                    self.assertEqual(
                        state.get_model('contenttypes', 'ContentType')
                        .objects.get(pk=ct)
                        .app_label,
                        label,
                    )
                    self.assertTrue(
                        state.get_model('auth', 'User')
                        .objects.get(pk=user.pk)
                        .user_permissions.filter(pk=perm)
                        .exists()
                    )
                self.assertEqual(set(connection.introspection.table_names()), tables)
        finally:
            self.migrate(leaves)
