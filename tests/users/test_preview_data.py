"""The full preview is linked, repeatable, private, and performs no external I/O."""

from collections import Counter
from io import StringIO
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.planning.models import StaffDailyAvailability
from eures_beta.candidates import push
from eures_beta.candidates.models import (
    CandidateProfileReviewSuggestion,
    CandidatePushSubscription,
)
from eures_beta.employers.models import JobOffer
from eures_beta.introductions.models import (
    CandidateOfferConversation,
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateOfferReviewEvent,
    CandidateProfileSharing,
)
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.introductions import review_workflow
from eures_beta.users.models import User
from eures_beta.users.preview_data.report import model_counts
from eures_beta.users.preview_data.scenarios import identifier
from eures_beta.users.test_accounts import prepared_user

SETTINGS = dict(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=False,
)


@override_settings(**SETTINGS)
class PreviewDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with (
            patch(
                'requests.sessions.Session.request',
                side_effect=AssertionError('No network from initial seeding'),
            ),
            cls.captureOnCommitCallbacks(execute=True),
        ):
            call_command('seed_test_accounts', stdout=StringIO())

    def snapshot(self):
        return {
            model._meta.label: list(
                model.objects.order_by(model._meta.pk.name).values()
            )
            for model in apps.get_models()
            if model._meta.managed and not model._meta.proxy
        }

    def test_every_active_model_has_records_and_reseeding_preserves_all_rows(self):
        counts = model_counts()
        self.assertEqual(len(counts), 31)
        self.assertEqual(counts['planning.StaffDailyAvailability'], 1)
        self.assertFalse(
            {label: count for label, count in counts.items() if count == 0}
        )
        self.assertEqual(
            (
                counts['users.User'],
                counts['employers.JobOffer'],
                counts['matching.CandidateOfferMatch'],
            ),
            (9, 16, 18),
        )
        self.assertEqual(counts['employers.EmployerProfile'], 1)
        self.assertEqual(counts['followup.JobOfferSupport'], 16)
        self.assertEqual(counts['followup.MatchFollowup'], 3)
        self.assertEqual(counts['followup.MatchFollowupEvent'], 3)
        self.assertEqual(counts['followup.MatchConclusion'], 1)
        self.assertEqual(counts['followup.MatchConclusionEvent'], 1)
        before = self.snapshot()
        call_command('seed_test_accounts', stdout=StringIO())
        self.assertEqual(self.snapshot(), before)

    def test_no_external_service_is_called_even_when_callbacks_execute(self):
        with patch(
            'requests.sessions.Session.request',
            side_effect=AssertionError('No network from seeding'),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                call_command('seed_test_accounts', stdout=StringIO())

    def test_existing_edits_answers_and_closed_conversations_are_not_reset(self):
        availability = StaffDailyAvailability.objects.get()
        availability.present = False
        availability.save(update_fields=['present'])
        offer = JobOffer.objects.get(pk=identifier('open'))
        offer.data['title'] = 'Personal fictional trial edit'
        offer.save()
        thread = CandidateOfferConversation.objects.get(
            offer_review__match__offer=offer
        )
        thread.messages.first().delete()
        before = self.snapshot()
        call_command('seed_test_accounts', stdout=StringIO())
        self.assertEqual(self.snapshot(), before)

    def test_workflow_states_consents_and_repeated_refusals_are_coherent(self):
        self.assertEqual(
            Counter(CandidateOfferReviewAnswer.objects.values_list('value', flat=True)),
            {'yes': 163, 'no': 6},
        )
        self.assertTrue(
            all(
                review.answers.count() == 13
                for review in CandidateOfferReview.objects.all()
            )
        )
        self.assertEqual(
            Counter(CandidateOfferReviewEvent.objects.values_list('action', flat=True)),
            {'submitted': 12, 'claim': 8, 'validated': 5, 'clarify': 1, 'refused': 1},
        )
        self.assertEqual(
            Counter(CandidateProfileSharing.objects.values_list('agreed', flat=True)),
            {True: 8, False: 4},
        )
        self.assertTrue(
            {'ready', 'claimed', 'clarify', 'validated', 'refused'}.issubset(
                set(
                    CandidateOfferReview.objects.values_list(
                        'workflow_state', flat=True
                    )
                )
            )
        )
        self.assertEqual(
            set(CandidateOfferConversation.objects.values_list('state', flat=True)),
            {'requested', 'approved', 'declined', 'open'},
        )
        for thread in CandidateOfferConversation.objects.select_related(
            'offer_review__match__candidate', 'offer_review__match__offer'
        ):
            self.assertTrue(review_workflow.current(thread.offer_review))
            self.assertEqual(thread.candidate, thread.offer_review.match.candidate.user)
            self.assertEqual(thread.employer, thread.offer_review.match.offer.employer)
            self.assertEqual(thread.consent_at is None, thread.state == 'requested')
            self.assertEqual(
                thread.messages.count(), 3 if thread.state == 'open' else 0
            )
        self.assertEqual(CandidateProfileReviewSuggestion.objects.count(), 2)
        for suggestion in CandidateProfileReviewSuggestion.objects.all():
            self.assertEqual(len({row['offer'] for row in suggestion.evidence}), 3)

    def test_selectable_accounts_have_owned_records_and_private_conversations(self):
        for key in ('candidate-pwa', 'candidate-pwa-replay'):
            user = prepared_user(key)
            self.client.force_login(user)
            page = self.client.get(reverse('candidate_offer_inbox'))
            self.assertEqual(page.status_code, 200)
            self.assertGreaterEqual(len(page.context['entries']), 5)
            self.assertTrue(
                all(
                    row['review'].match.candidate.user_id == user.pk
                    for row in page.context['entries']
                )
            )
            self.assertTrue(page.context['shared_conversations'])
        for key in ('employer', 'adviser', 'admin'):
            self.client.force_login(prepared_user(key))
            self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertTrue(CandidateOfferMatch.objects.filter(decision='refused').exists())

    def test_previous_two_employers_consolidate_without_losing_rich_trials(self):
        from django.utils import timezone
        from eures_beta.employers.models import EmployerProfile
        from eures_beta.invitations.models import Invitation
        from eures_beta.introductions.models import CandidateOfferConversationMessage
        from eures_beta.users.demo_employers import LEGACY_EMPLOYER_EMAIL

        employer = prepared_user('employer')
        legacy = User.objects.create_user(LEGACY_EMPLOYER_EMAIL, kind='employer')
        offer_ids = [
            identifier(key)
            for key in ('claimed', 'approved', 'open-replay', 'declined')
        ]
        offer_ids += list(
            JobOffer.objects.filter(session_key='matching-trial').values_list(
                'pk', flat=True
            )
        )
        JobOffer.objects.filter(pk__in=offer_ids).update(employer=legacy)
        conversations = CandidateOfferConversation.objects.filter(
            offer_review__match__offer_id__in=offer_ids
        )
        conversation_ids = list(conversations.values_list('pk', flat=True))
        conversations.update(employer=legacy)
        CandidateOfferConversationMessage.objects.filter(
            conversation_id__in=conversation_ids, author=employer
        ).update(author=legacy)
        EmployerProfile.objects.create(
            user=legacy, response_coverage='selected', response_time='one_two_weeks'
        )
        Invitation.objects.create(
            email=legacy.email,
            recipient=legacy,
            sender_adviser=prepared_user('adviser'),
            accepted_at=timezone.now(),
        )
        expected = self.snapshot()
        expected['users.User'] = [
            row for row in expected['users.User'] if row['id'] != legacy.pk
        ]
        expected['employers.EmployerProfile'] = [
            row
            for row in expected['employers.EmployerProfile']
            if row['user_id'] != legacy.pk
        ]
        for row in expected['introductions.CandidateOfferConversationMessage']:
            if row['author_id'] == legacy.pk:
                row['author_id'] = employer.pk
        for row in expected['invitations.Invitation']:
            if row['recipient_id'] == legacy.pk:
                row['recipient_id'] = None
        for row in expected['employers.JobOffer']:
            if row['employer_id'] == legacy.pk:
                row['employer_id'] = employer.pk
        for row in expected['introductions.CandidateOfferConversation']:
            if row['employer_id'] == legacy.pk:
                row['employer_id'] = employer.pk
        call_command('seed_test_accounts', stdout=StringIO())
        self.assertEqual(self.snapshot(), expected)
        call_command('seed_test_accounts', stdout=StringIO())
        self.assertEqual(self.snapshot(), expected)
        self.assertFalse(JobOffer.objects.exclude(employer=employer).exists())
        for thread in CandidateOfferConversation.objects.all():
            self.assertTrue(review_workflow.current(thread.offer_review))

    def test_push_fixtures_are_undeliverable_and_sessions_are_not_authentication(self):
        from django.contrib.sessions.models import Session

        for subscription in CandidatePushSubscription.objects.all():
            self.assertFalse(push.valid_endpoint(subscription.endpoint))
            with patch(
                'requests.sessions.Session.request',
                side_effect=AssertionError('No Push to fixture endpoints'),
            ):
                self.assertFalse(
                    push.send(subscription.candidate, {'body': 'Fictional'})
                )
        for session in Session.objects.all():
            self.assertNotIn('_auth_user_id', session.get_decoded())

    def test_report_is_read_only_and_does_not_export_values(self):
        before = self.snapshot()
        output = StringIO()
        call_command('seed_test_accounts', report=True, stdout=output)
        self.assertEqual(before, self.snapshot())
        self.assertIn('introductions.CandidateOfferConversation: 5', output.getvalue())
        self.assertNotIn('@', output.getvalue())

    def test_full_dataset_is_refused_in_production_or_a_nonfictional_database(self):
        for settings in (
            {'DJANGO_ENVIRONMENT': 'production'},
            {'DEMO_ACCOUNTS_ENABLED': False},
            {'EMAIL_DELIVERY_ENABLED': True},
        ):
            with (
                self.subTest(settings=settings),
                self.settings(**settings),
                self.assertRaises(CommandError),
            ):
                call_command('seed_test_accounts', stdout=StringIO())
        User.objects.create_user('ordinary@example.org', kind='candidate')
        before = self.snapshot()
        with self.assertRaises(CommandError):
            call_command('seed_test_accounts', stdout=StringIO())
        self.assertEqual(before, self.snapshot())
