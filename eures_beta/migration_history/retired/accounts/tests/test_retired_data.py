from eures_beta.migration_history.testing import (
    pre_retirement_targets,
    restore_current_schema,
)
from django.db.migrations.executor import MigrationExecutor
from importlib import import_module

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone


class RetiredDataTests(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(pre_retirement_targets())
        self.apps = executor.loader.project_state(pre_retirement_targets()).apps

    def tearDown(self):
        restore_current_schema()

    def clean(self):
        module = import_module(
            'eures_beta.migration_history.retired.accounts.migrations.0002_remove_legacy_demo_accounts'
        )
        with connection.schema_editor(atomic=False) as editor:
            module.remove_legacy_demo(self.apps, editor)

    def test_only_reserved_accounts_and_scenario_are_removed_and_import_survives(self):
        Profile = self.apps.get_model('accounts', 'Profile')
        Candidate = self.apps.get_model('candidates', 'Candidate')
        Offer = self.apps.get_model('offers', 'Offer')
        Question = self.apps.get_model('offers', 'Question')
        Match = self.apps.get_model('matching', 'Match')
        Answer = self.apps.get_model('matching', 'Answer')
        Conversation = self.apps.get_model('conversations', 'Conversation')
        Message = self.apps.get_model('conversations', 'Message')
        EmployerImport = self.apps.get_model('employers', 'EmployerImport')
        users = {}
        for role in ('adviser', 'employer', 'candidate', 'admin'):
            user = self.apps.get_model('auth', 'User').objects.create(
                username=f'{role}@example.invalid', password='!'
            )
            Profile.objects.create(user=user, role=role, verified=True)
            users[role] = user
        operator = get_user_model().objects.create_superuser(
            username='operator@example.invalid', password='fictional-password'
        )
        candidate = Candidate.objects.create(user=users['candidate'])
        offer = Offer.objects.create(
            employer=users['employer'], adviser=users['adviser']
        )
        question = Question.objects.create(offer=offer)
        match = Match.objects.create(offer=offer, candidate=candidate)
        Answer.objects.create(match=match, question=question)
        conversation = Conversation.objects.create(
            match=match, opened_by=users['adviser']
        )
        Message.objects.create(
            conversation=conversation,
            sender=users['candidate'],
            body='Fictional message',
        )
        draft = EmployerImport.objects.create(
            adviser=users['adviser'],
            session_key='fictional',
            email='real-test@example.invalid',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'description': 'Preserved current import'},
        )
        self.clean()
        self.clean()
        self.assertEqual(
            list(get_user_model().objects.values_list('pk', flat=True)), [operator.pk]
        )
        for model in (
            Profile,
            Candidate,
            Offer,
            Question,
            Match,
            Answer,
            Conversation,
            Message,
        ):
            self.assertFalse(model.objects.exists(), model.__name__)
        draft.refresh_from_db()
        self.assertIsNone(draft.adviser_id)
        self.assertEqual(draft.data, {'description': 'Preserved current import'})

    def test_reused_reserved_operator_account_is_not_deleted(self):
        user = get_user_model().objects.create_superuser(
            username='admin@example.invalid', password='fictional-password'
        )
        with self.assertRaisesRegex(RuntimeError, 'operator privileges'):
            self.clean()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_empty_legacy_tables_are_removed_but_current_import_remains(self):
        draft = self.apps.get_model('employers', 'EmployerImport').objects.create(
            session_key='fictional',
            email='test@example.invalid',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'description': 'Preserved import'},
        )
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        tables = connection.introspection.table_names()
        for label, name in import_module(
            'eures_beta.migration_history.retired.accounts.migrations.0003_verify_retired_tables_empty'
        ).LEGACY_MODELS:
            self.assertNotIn(self.apps.get_model(label, name)._meta.db_table, tables)
        from eures_beta.employers.models import EmployerImport

        self.assertEqual(
            EmployerImport.objects.get(pk=draft.pk).data['description'],
            'Preserved import',
        )

    def test_non_scenario_offer_blocks_table_removal(self):
        user = self.apps.get_model('auth', 'User').objects.create(
            username='other@example.invalid', password='!'
        )
        self.apps.get_model('offers', 'Offer').objects.create(
            employer_id=user.pk, adviser_id=user.pk
        )
        executor = MigrationExecutor(connection)
        with self.assertRaisesRegex(RuntimeError, 'refusing table removal'):
            executor.migrate(executor.loader.graph.leaf_nodes())
        self.assertEqual(self.apps.get_model('offers', 'Offer').objects.count(), 1)
