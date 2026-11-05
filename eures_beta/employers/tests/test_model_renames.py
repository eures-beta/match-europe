"""Exercise upgrade and rollback with rows, ownership, grants and audit links."""

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

BEFORE = ('employers', '0002_unify_users')
AFTER = ('employers', '0003_rename_employer_models')
NAMES = (
    ('EmployerCompany', 'Company'),
    ('EmployerMembership', 'CompanyMembership'),
    ('EmployerImport', 'JobOffer'),
)
TABLES = (
    'journeys_employercompany',
    'journeys_employermembership',
    'journeys_employerimport',
    'journeys_employeremaillink',
    'journeys_employersearchoperation',
    'journeys_employersearchevent',
)


class ModelRenameMigrationTests(TransactionTestCase):
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

    def snapshot(self):
        with connection.cursor() as cursor:
            result = {}
            for table in TABLES:
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                result[table] = (oid, cursor.fetchall())
            return result

    def test_upgrade_and_reverse_preserve_tables_rows_grants_and_audit_references(self):
        apps = self.migrate(BEFORE)
        User = apps.get_model('users', 'User')
        user = User.objects.create(
            email='owner@example.invalid', kind='employer', password='!'
        )
        company = apps.get_model('employers', 'EmployerCompany').objects.create(
            name='Fictional company'
        )
        apps.get_model('employers', 'EmployerMembership').objects.create(
            company=company, person=user
        )
        Offer = apps.get_model('employers', 'EmployerImport')
        offer = Offer.objects.create(
            company=company,
            created_by=user,
            session_key='fictional-session',
            email=user.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': 'Preserved offer'},
            contact={'name': 'Fictional contact'},
        )
        Offer.objects.create(
            company=company,
            created_by=user,
            duplicated_from=offer,
            session_key='fictional-copy',
            email=user.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
        )
        apps.get_model('employers', 'EmployerEmailLink').objects.create(
            pending_import=offer,
            email=user.email,
            digest='b' * 64,
            expires=timezone.now(),
        )
        operation = apps.get_model(
            'employers', 'EmployerSearchOperation'
        ).objects.create(
            offer=offer,
            requested_by=user,
            revision=1,
            state='started',
            scenario='fictional',
        )
        apps.get_model('employers', 'EmployerSearchEvent').objects.create(
            operation=operation,
            actor=user,
            state='started',
        )
        CT = apps.get_model('contenttypes', 'ContentType')
        Permission = apps.get_model('auth', 'Permission')
        group = apps.get_model('auth', 'Group').objects.create(
            name='fictional-observers'
        )
        user.groups.add(group)
        metadata = []
        for old, new in NAMES:
            content_type, _ = CT.objects.get_or_create(
                app_label='employers', model=old.lower()
            )
            for action in ('add', 'change', 'delete', 'view'):
                permission, _ = Permission.objects.get_or_create(
                    content_type=content_type,
                    codename=f'{action}_{old.lower()}',
                    defaults={'name': 'Preserved permission'},
                )
                user.user_permissions.add(permission)
                group.permissions.add(permission)
                metadata.append(
                    (content_type.pk, permission.pk, old.lower(), new.lower(), action)
                )
        log = apps.get_model('admin', 'LogEntry').objects.create(
            user_id=user.pk,
            content_type_id=metadata[0][0],
            object_id=str(company.pk),
            object_repr='Fictional company',
            action_flag=1,
        )
        snapshot = self.snapshot()
        with CaptureQueriesContext(connection) as queries:
            apps = self.migrate(AFTER)
        self.assertFalse(
            any(
                q['sql'].lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP '))
                for q in queries
            )
        )
        self.assertEqual(self.snapshot(), snapshot)
        self.assertTrue(user.groups.filter(pk=group.pk).exists())
        for old, new in NAMES:
            with self.assertRaises(LookupError):
                apps.get_model('employers', old)
            self.assertIsNotNone(apps.get_model('employers', new))
        CT = apps.get_model('contenttypes', 'ContentType')
        Permission = apps.get_model('auth', 'Permission')
        for ct_id, permission_id, old, new, action in metadata:
            self.assertEqual(CT.objects.get(pk=ct_id).model, new)
            self.assertEqual(
                Permission.objects.get(pk=permission_id).codename, f'{action}_{new}'
            )
            self.assertTrue(user.user_permissions.filter(pk=permission_id).exists())
            self.assertTrue(group.permissions.filter(pk=permission_id).exists())
        self.assertEqual(
            apps.get_model('admin', 'LogEntry').objects.get(pk=log.pk).content_type_id,
            metadata[0][0],
        )
        self.migrate(BEFORE)
        self.assertEqual(self.snapshot(), snapshot)
        for ct_id, permission_id, old, new, action in metadata:
            self.assertEqual(CT.objects.get(pk=ct_id).model, old)
            self.assertEqual(
                Permission.objects.get(pk=permission_id).codename, f'{action}_{old}'
            )
