from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class DomainMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_rows_relations_tables_and_permission_ids_survive_round_trip(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before = [
            ('journeys', '0016_remove_employerimport_company_and_more'),
            ('matching', None),
        ]
        try:
            old = self.migrate(before)
            user = old.get_model('auth', 'User').objects.create(
                username='matching@example.invalid'
            )
            candidate = old.get_model('candidates', 'Candidate').objects.create(
                user_id=user.pk, name='Fictional candidate'
            )
            offer = old.get_model('offers', 'Offer').objects.create(
                employer_id=user.pk, adviser_id=user.pk, title='Fictional offer'
            )
            question = old.get_model('offers', 'Question').objects.create(
                offer_id=offer.pk, text='Saved question'
            )
            match = old.get_model('journeys', 'Match').objects.create(
                offer_id=offer.pk,
                candidate_id=candidate.pk,
                explanation='Saved explanation',
                candidate_agreement=True,
            )
            old.get_model('journeys', 'Answer').objects.create(
                match_id=match.pk, question_id=question.pk, text='Saved answer'
            )
            old.get_model('conversations', 'Conversation').objects.create(
                match_id=match.pk, opened_by_id=user.pk
            )
            snapshots = {}
            permissions = []
            for name in ['Match', 'Answer']:
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
            if 'matching' == 'matching':
                model = old.get_model('conversations', 'Conversation')
                snapshots[model._meta.db_table] = list(
                    model.objects.order_by('pk').values()
                )
            tables = set(connection.introspection.table_names())
            for targets, label in [(leaves, 'matching'), (before, 'journeys')]:
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
