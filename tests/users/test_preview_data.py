"""The full preview is linked, repeatable, private, and performs no external I/O."""

from io import StringIO
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.candidates import push
from eures_beta.candidates.models import (
    CandidateProfileReviewSuggestion,
    CandidatePushSubscription,
)
from eures_beta.employers.models import JobOffer
from eures_beta.matching.models import (
    CandidateOfferConversation,
    CandidateOfferReview,
    CandidateOfferMatch,
)
from eures_beta.matching import review_workflow
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
        self.assertEqual(len(counts), 25)
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
        for key in ('employer', 'matching-employer', 'adviser', 'admin'):
            self.client.force_login(prepared_user(key))
            self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertTrue(CandidateOfferMatch.objects.filter(decision='refused').exists())

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
        self.assertIn('matching.CandidateOfferConversation: 5', output.getvalue())
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
