"""The final schema supports fresh installs and databases transitioned earlier."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from eures_beta.employers.models import (
    EmployerCompany,
    EmployerMembership,
    EmployerImport,
    EmployerEmailLink,
    EmployerSearchOperation,
    EmployerSearchEvent,
)

BASELINE = ('employers', '0001_autonomous_schema')

CURRENT_MODELS = (
    EmployerCompany,
    get_user_model(),
    EmployerMembership,
    EmployerImport,
    EmployerEmailLink,
    EmployerSearchOperation,
    EmployerSearchEvent,
)

LEGACY_TABLES = (
    'journeys_profile',
    'journeys_accesstoken',
    'journeys_event',
    'journeys_candidate',
    'journeys_offer',
    'journeys_question',
    'journeys_match',
    'journeys_answer',
    'journeys_conversation',
    'journeys_message',
    'journeys_document',
    'journeys_notification',
    'journeys_employeridentity',
    'auth_user',
)


class AutonomousMigrationTests(TransactionTestCase):
    def test_current_schema_keeps_the_baseline_without_retired_identity_tables(self):
        self.assert_no_legacy_tables()
        applied = MigrationRecorder(connection).applied_migrations()
        self.assertIn(BASELINE, applied)
        self.assertIn(('users', '0002_kind_immutable'), applied)

    def assert_no_legacy_tables(self):
        tables = connection.introspection.table_names()
        for table in LEGACY_TABLES:
            self.assertNotIn(table, tables)
        for model in CURRENT_MODELS:
            self.assertIn(model._meta.db_table, tables)

    def test_transitioned_database_preserves_all_current_data_without_ddl(self):
        user = get_user_model().objects.create_user(
            'operator@example.invalid', kind='adviser'
        )
        person = get_user_model().objects.create_user(
            'person@example.invalid', kind='employer'
        )
        company = EmployerCompany.objects.create(name='Fictional workplace')
        EmployerMembership.objects.create(company=company, person=person)
        draft = EmployerImport.objects.create(
            company=company,
            created_by=person,
            adviser=user,
            session_key='fictional',
            email=person.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'description': 'Preserved extracted text'},
            contact={'name': 'Fictional contact'},
        )
        EmployerEmailLink.objects.create(
            pending_import=draft,
            email=person.email,
            digest='a' * 64,
            expires=timezone.now(),
        )
        operation = EmployerSearchOperation.objects.create(
            offer=draft,
            requested_by=person,
            revision=1,
            state='started',
            scenario='fictional',
        )
        EmployerSearchEvent.objects.create(
            operation=operation, actor=person, state='started'
        )
        content_type = ContentType.objects.get_for_model(EmployerImport)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename='view_employerimport',
            defaults={'name': 'Fictional permission'},
        )
        user.user_permissions.add(permission)
        session = SessionStore()
        session['pending_offer_source'] = {
            'description': 'Preserved pending extraction'
        }
        session.save()
        snapshots = {
            model: list(model.objects.order_by('pk').values())
            for model in CURRENT_MODELS
        }
        saved_session = Session.objects.get(pk=session.session_key).session_data
        recorder = MigrationRecorder(connection)
        self.assertIn(BASELINE, recorder.applied_migrations())
        # Leftover records from the prior release are historical metadata only.
        recorder.record_applied('journeys', '0001_initial')

        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        self.assertEqual(
            executor.migration_plan(executor.loader.graph.leaf_nodes()), []
        )
        with CaptureQueriesContext(connection) as queries:
            executor.migrate(executor.loader.graph.leaf_nodes())
        self.assertFalse(
            any(
                q['sql'].lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP '))
                for q in queries
            )
        )
        self.assertIn(BASELINE, recorder.applied_migrations())
        for model, rows in snapshots.items():
            self.assertEqual(list(model.objects.order_by('pk').values()), rows)
        self.assertEqual(
            Session.objects.get(pk=session.session_key).session_data, saved_session
        )
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertEqual(
            ContentType.objects.get(pk=content_type.pk).app_label, 'employers'
        )
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
