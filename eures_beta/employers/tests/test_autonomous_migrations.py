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
    EmployerIdentity,
    EmployerMembership,
    EmployerImport,
    EmployerEmailLink,
    EmployerSearchOperation,
    EmployerSearchEvent,
)

BASELINE = ('employers', '0001_autonomous_schema')

CURRENT_MODELS = (
    EmployerCompany,
    EmployerIdentity,
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
)


class AutonomousMigrationTests(TransactionTestCase):
    def migrate_current(self):
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def assert_no_legacy_tables(self):
        tables = connection.introspection.table_names()
        for table in LEGACY_TABLES:
            self.assertNotIn(table, tables)
        for model in CURRENT_MODELS:
            self.assertIn(model._meta.db_table, tables)

    def test_fresh_install_creates_only_current_business_tables(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('employers', None)])
        ContentType.objects.filter(app_label='employers').delete()
        ContentType.objects.clear_cache()
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertEqual(
            [(m.app_label, m.name, backwards) for m, backwards in plan],
            [(*BASELINE, False)],
        )
        with CaptureQueriesContext(connection) as queries:
            executor.migrate(executor.loader.graph.leaf_nodes())
        created_tables = [
            q['sql']
            for q in queries
            if q['sql'].lstrip().upper().startswith('CREATE TABLE')
        ]
        self.assertEqual(len(created_tables), 7)
        for table in LEGACY_TABLES:
            self.assertFalse(
                any('"' + table + '"' in sql for sql in created_tables), table
            )
        self.assert_no_legacy_tables()
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(EmployerImport.objects.exists())

    def test_transitioned_database_preserves_all_current_data_without_ddl(self):
        user = get_user_model().objects.create_user('operator@example.invalid')
        person = EmployerIdentity.objects.create(email='person@example.invalid')
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

    def test_cleanup_refuses_existing_database_without_transition_marker(self):
        draft = EmployerImport.objects.create(
            session_key='fictional',
            email='contact@example.invalid',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'description': 'Preserve this draft'},
        )
        recorder = MigrationRecorder(connection)
        recorder.record_unapplied(*BASELINE)
        # Simulate an installation that only ran the pre-transition release.
        recorder.record_applied('journeys', '0001_initial')
        try:
            with CaptureQueriesContext(connection) as queries:
                with self.assertRaisesRegex(
                    RuntimeError, 'Deploy the transition release'
                ):
                    self.migrate_current()
            self.assertFalse(
                any(
                    q['sql'].lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP '))
                    for q in queries
                )
            )
            draft.refresh_from_db()
            self.assertEqual(draft.data, {'description': 'Preserve this draft'})
            self.assertNotIn(BASELINE, recorder.applied_migrations())
        finally:
            # Restore the test fixture marker so Django can flush normally.
            recorder.record_applied(*BASELINE)
