from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PreservedModelMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_rows_relations_and_permission_ids_survive_forward_and_reverse(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        old_targets = [
            ('journeys', '0011_alter_candidate_document_alter_offer_document_and_more'),
            ('candidates', None),
        ]
        try:
            old = self.migrate(old_targets)
            user = old.get_model('auth', 'User').objects.create(
                username='candidates-migration@example.invalid'
            )
            candidate = old.get_model('journeys', 'Candidate').objects.create(
                user_id=user.pk,
                name='Fictional candidate',
                experience='Saved experience',
            )
            offer = old.get_model('journeys', 'Offer').objects.create(
                employer_id=user.pk, adviser_id=user.pk
            )
            old.get_model('journeys', 'Match').objects.create(
                offer_id=offer.pk,
                candidate_id=candidate.pk,
                explanation='Fictional preserved relation',
            )
            snapshots = {
                name: list(
                    old.get_model('journeys', name).objects.order_by('pk').values()
                )
                for name in ['Candidate', 'Match']
            }
            types = old.get_model('contenttypes', 'ContentType')
            content_type, _ = types.objects.get_or_create(
                app_label='journeys', model='candidate'
            )
            permission, _ = old.get_model('auth', 'Permission').objects.get_or_create(
                content_type_id=content_type.pk,
                codename='view_candidate',
                defaults={'name': 'Fictional permission'},
            )
            user.user_permissions.add(permission)
            tables = set(connection.introspection.table_names())
            new = self.migrate(leaves)
            for name, snapshot in snapshots.items():
                label = 'candidates' if name in ['Candidate'] else 'journeys'
                self.assertEqual(
                    list(new.get_model(label, name).objects.order_by('pk').values()),
                    snapshot,
                )
            self.assertEqual(
                new.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .app_label,
                'candidates',
            )
            self.assertTrue(
                new.get_model('auth', 'User')
                .objects.get(pk=user.pk)
                .user_permissions.filter(pk=permission.pk)
                .exists()
            )
            self.assertEqual(set(connection.introspection.table_names()), tables)
            restored = self.migrate(old_targets)
            for name, snapshot in snapshots.items():
                self.assertEqual(
                    list(
                        restored.get_model('journeys', name)
                        .objects.order_by('pk')
                        .values()
                    ),
                    snapshot,
                )
            self.assertEqual(
                restored.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .app_label,
                'journeys',
            )
            self.assertTrue(
                restored.get_model('auth', 'User')
                .objects.get(pk=user.pk)
                .user_permissions.filter(pk=permission.pk)
                .exists()
            )
            self.assertEqual(set(connection.introspection.table_names()), tables)
        finally:
            self.migrate(leaves)
