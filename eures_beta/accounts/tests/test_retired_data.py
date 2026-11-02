from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from eures_beta.accounts.models import Profile
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer, Question
from eures_beta.matching.models import Match, Answer
from eures_beta.conversations.models import Conversation, Message
from eures_beta.employers.models import EmployerImport


class RetiredDataTests(TestCase):
    def clean(self):
        module = import_module(
            'eures_beta.accounts.migrations.0002_remove_legacy_demo_accounts'
        )
        with connection.schema_editor(atomic=False) as editor:
            module.remove_legacy_demo(apps, editor)

    def test_only_reserved_accounts_and_scenario_are_removed_and_import_survives(self):
        users = {}
        for role in ('adviser', 'employer', 'candidate', 'admin'):
            user = get_user_model().objects.create_user(
                username=f'{role}@example.invalid'
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
