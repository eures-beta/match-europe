"""Exercise the normal Django replacement loader on real PostgreSQL schemas."""

from importlib import import_module

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
from eures_beta.migration_history.testing import (
    HistoricalMigrationExecutor,
    pre_retirement_targets,
    restore_current_schema,
)

BASELINE = ('employers', '0001_autonomous_schema')
BASELINE_CLASS = import_module(
    'eures_beta.employers.migrations.' + BASELINE[1]
).Migration
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
    def tearDown(self):
        # Fixtures in deliberately incomplete historical schemas must not leak
        # into the following test or Django's flush of current models.
        restore_current_schema()

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
        original = HistoricalMigrationExecutor(connection)
        original.migrate([('journeys', None)])
        original.recorder.record_unapplied(*BASELINE)
        ContentType.objects.filter(
            app_label__in={label for label, _ in BASELINE_CLASS.replaces}
        ).delete()

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

    def test_completed_history_records_squash_without_ddl_or_data_changes(self):
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
        self.assertTrue(
            all(key in recorder.applied_migrations() for key in BASELINE_CLASS.replaces)
        )
        recorder.record_unapplied(*BASELINE)

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

    def test_partial_history_uses_original_cleanup_and_preserves_current_import(self):
        original = HistoricalMigrationExecutor(connection)
        original.migrate(pre_retirement_targets())
        state = original.loader.project_state(pre_retirement_targets()).apps
        users = {}
        for role in ('adviser', 'employer', 'candidate', 'admin'):
            users[role] = state.get_model('auth', 'User').objects.create(
                username=f'{role}@example.invalid', password='!'
            )
            state.get_model('accounts', 'Profile').objects.create(
                user_id=users[role].pk, role=role
            )
        candidate = state.get_model('candidates', 'Candidate').objects.create(
            user_id=users['candidate'].pk
        )
        offer = state.get_model('offers', 'Offer').objects.create(
            employer_id=users['employer'].pk, adviser_id=users['adviser'].pk
        )
        state.get_model('offers', 'Question').objects.create(
            offer_id=offer.pk, text='Fictional question'
        )
        state.get_model('matching', 'Match').objects.create(
            offer_id=offer.pk, candidate_id=candidate.pk
        )
        draft = EmployerImport.objects.create(
            adviser_id=users['adviser'].pk,
            session_key='fictional',
            email='contact@example.invalid',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'description': 'Preserved draft'},
        )

        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        self.assertNotIn(BASELINE, executor.loader.graph.nodes)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertIn(
            ('accounts', '0002_remove_legacy_demo_accounts'),
            [(m.app_label, m.name) for m, _ in plan],
        )
        executor.migrate(executor.loader.graph.leaf_nodes())
        self.assert_no_legacy_tables()
        self.assertFalse(get_user_model().objects.exists())
        draft.refresh_from_db()
        self.assertEqual(draft.data, {'description': 'Preserved draft'})
        self.assertIsNone(draft.adviser_id)
        self.assertIn(BASELINE, MigrationRecorder(connection).applied_migrations())

    def test_partial_history_still_refuses_to_drop_non_scenario_data(self):
        original = HistoricalMigrationExecutor(connection)
        original.migrate(pre_retirement_targets())
        state = original.loader.project_state(pre_retirement_targets()).apps
        user = state.get_model('auth', 'User').objects.create(
            username='other@example.invalid', password='!'
        )
        offer = state.get_model('offers', 'Offer').objects.create(
            employer_id=user.pk, adviser_id=user.pk
        )
        with self.assertRaisesRegex(RuntimeError, 'refusing table removal'):
            self.migrate_current()
        self.assertTrue(
            state.get_model('offers', 'Offer').objects.filter(pk=offer.pk).exists()
        )
