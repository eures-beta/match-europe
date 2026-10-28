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
            ('journeys', '0015_remove_event_actor_remove_profile_adviser_and_more'),
            ('employers', None),
        ]
        try:
            old = self.migrate(before)
            user = old.get_model('auth', 'User').objects.create(
                username='employers@example.invalid'
            )
            person = old.get_model('journeys', 'EmployerIdentity').objects.create(
                email='person@example.invalid'
            )
            company = old.get_model('journeys', 'EmployerCompany').objects.create(
                name='Fictional workplace'
            )
            old.get_model('journeys', 'EmployerMembership').objects.create(
                person_id=person.pk, company_id=company.pk, active=False
            )
            draft = old.get_model('journeys', 'EmployerImport').objects.create(
                company_id=company.pk,
                created_by_id=person.pk,
                adviser_id=user.pk,
                session_key='fictional',
                email='contact@example.invalid',
                preparation_agreed_at=timezone.now(),
                source_kind='text',
                data={'title': 'Saved title'},
                contact={'name': 'Fictional contact'},
            )
            old.get_model('journeys', 'EmployerEmailLink').objects.create(
                pending_import_id=draft.pk,
                email=person.email,
                digest='b' * 64,
                expires=timezone.now(),
                used=True,
            )
            op = old.get_model('journeys', 'EmployerSearchOperation').objects.create(
                offer_id=draft.pk,
                requested_by_id=person.pk,
                revision=1,
                state='uncertain',
                scenario='fictional',
            )
            old.get_model('journeys', 'EmployerSearchEvent').objects.create(
                operation_id=op.pk, actor_id=person.pk, state='uncertain'
            )
            snapshots = {}
            permissions = []
            for name in [
                'EmployerIdentity',
                'EmployerCompany',
                'EmployerMembership',
                'EmployerImport',
                'EmployerEmailLink',
                'EmployerSearchOperation',
                'EmployerSearchEvent',
            ]:
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
            if 'employers' == 'matching':
                model = old.get_model('conversations', 'Conversation')
                snapshots[model._meta.db_table] = list(
                    model.objects.order_by('pk').values()
                )
            tables = set(connection.introspection.table_names())
            for targets, label in [(leaves, 'employers'), (before, 'journeys')]:
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
