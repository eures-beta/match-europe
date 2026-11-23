from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import offer_review_services, services, review_workflow
from eures_beta.matching.models import (
    CandidateOfferReview,
    CandidateOfferMatch,
    CandidateOfferConversation,
)
from tests.matching.test_dialogue import SETTINGS
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user


@override_settings(**{**SETTINGS, 'ALBERT_SIMULATED': True})
class CandidateOfferConversationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        cls.adviser = prepared_user('adviser')
        cls.adviser.groups.clear()
        cls.adviser.user_permissions.clear()
        cls.other = User.objects.create_user(
            'other@matching-trial.invalid', kind='adviser'
        )
        cls.other.groups.clear()
        cls.other.user_permissions.clear()
        cls.match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        cls.candidate = cls.match.candidate.user
        cls.employer = cls.match.offer.employer

    def setUp(self):
        (
            self.adviser_client,
            self.candidate_client,
            self.employer_client,
            self.other_client,
        ) = (Client(), Client(), Client(), Client())
        for client, user in (
            (self.adviser_client, self.adviser),
            (self.candidate_client, self.candidate),
            (self.employer_client, self.employer),
            (self.other_client, self.other),
        ):
            client.force_login(user)
        evaluation = services.calculate(self.match.candidate, self.match.offer)
        self.adviser_client.post(
            reverse('adviser_match', args=[self.match.pk]),
            {
                'action': 'retained',
                'evaluation': evaluation.pk,
            },
        )
        self.review = CandidateOfferReview.objects.get(match=self.match)
        self.start = reverse('shared_conversation_start', args=[self.review.pk])

    def request_conversation(self):
        self.assertEqual(
            self.adviser_client.post(self.start, {'body': 'Introduction'}).status_code,
            404,
        )
        for row in offer_review_services.review_state(self.review)['rows']:
            if row['askable']:
                offer_review_services.answer(
                    self.candidate,
                    self.review.pk,
                    row['key'],
                    row['fingerprint'],
                    'yes',
                    dialogue={'prompt': 'Private Albert dialogue'},
                )
        state = offer_review_services.review_state(self.review)
        offer_review_services.agree(
            self.candidate, self.review.pk, state['fingerprint'], True
        )
        self.review.refresh_from_db()
        review_workflow.handle(
            self.adviser,
            self.review.pk,
            'claim',
            self.review.workflow_version,
            state['fingerprint'],
        )
        self.review.refresh_from_db()
        review_workflow.handle(
            self.adviser,
            self.review.pk,
            'validated',
            self.review.workflow_version,
            state['fingerprint'],
            public_message='We can proceed.',
        )
        self.assertEqual(
            self.other_client.post(self.start, {'body': 'Intrusion'}).status_code, 404
        )
        response = self.adviser_client.post(self.start, {'body': 'Introduction'})
        self.assertEqual(response.status_code, 302)
        return response.url

    def test_three_participants_and_unread_messages(self):
        url = self.request_conversation()
        self.assertEqual(self.employer_client.get(url).status_code, 404)
        self.assertEqual(
            self.adviser_client.post(url, {'action': 'open'}).status_code, 404
        )
        self.assertContains(
            self.candidate_client.get(reverse('candidate_offer_inbox')),
            url.split('?')[0],
        )
        self.assertEqual(
            self.candidate_client.post(url, {'action': 'approve'}).status_code, 302
        )
        self.assertEqual(self.employer_client.get(url).status_code, 404)
        self.assertEqual(
            self.adviser_client.post(url, {'action': 'open'}).status_code, 302
        )
        self.assertEqual(
            self.adviser_client.post(url, {'action': 'open'}).status_code, 404
        )
        dashboard = reverse('dashboard') + '?lang=en'
        self.assertContains(self.employer_client.get(dashboard), 'Unread messages')
        self.assertContains(self.employer_client.get(url), 'Introduction')
        self.assertNotContains(self.employer_client.get(dashboard), 'Unread messages')
        self.assertEqual(self.other_client.get(url).status_code, 404)
        self.assertEqual(
            self.other_client.post(
                url, {'action': 'send', 'body': 'Intrusion'}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.employer_client.post(
                url, {'action': 'send', 'body': 'Tuesday at 10?'}
            ).status_code,
            302,
        )
        self.assertContains(self.candidate_client.get(url), 'Tuesday at 10?')
        self.assertEqual(
            self.candidate_client.post(
                url, {'action': 'send', 'body': 'Yes, thank you.'}
            ).status_code,
            302,
        )
        self.assertContains(self.adviser_client.get(url), 'Yes, thank you.')
        self.assertNotContains(self.employer_client.get(url), 'Private Albert dialogue')
        self.assertTrue(self.review.profile_sharings.exists())
        self.assertEqual(CandidateOfferConversation.objects.get().messages.count(), 3)

    def test_candidate_refusal_leaves_employer_out(self):
        url = self.request_conversation()
        self.assertEqual(
            self.candidate_client.post(url, {'action': 'decline'}).status_code, 302
        )
        self.assertEqual(
            self.adviser_client.post(url, {'action': 'open'}).status_code, 404
        )
        self.assertEqual(self.employer_client.get(url).status_code, 404)
        self.assertFalse(CandidateOfferConversation.objects.get().messages.exists())

    def test_takeover_preserves_messages_from_the_previous_adviser(self):
        url = self.request_conversation()
        self.candidate_client.post(url, {'action': 'approve'})
        self.adviser_client.post(url, {'action': 'open'})
        self.review.refresh_from_db()
        review_workflow.handle(
            self.other,
            self.review.pk,
            'takeover',
            self.review.workflow_version,
            offer_review_services.review_state(self.review)['fingerprint'],
            internal_note='Covering the previous adviser',
        )
        self.assertContains(self.other_client.get(url), 'Introduction')
        self.assertEqual(
            self.other_client.post(
                url, {'action': 'send', 'body': 'I am taking over the follow-up.'}
            ).status_code,
            302,
        )
        self.assertContains(self.candidate_client.get(url), 'Introduction')
        self.assertContains(
            self.candidate_client.get(url), 'I am taking over the follow-up.'
        )
        self.assertEqual(self.adviser_client.get(url).status_code, 404)

    def test_start_rechecks_ownership_after_waiting_for_the_lock(self):
        self.request_conversation()
        match = self.match

        def changed_while_waiting(**kwargs):
            CandidateOfferReview.objects.filter(pk=self.review.pk).update(
                assigned_to_adviser=self.other
            )
            return match

        with patch(
            'eures_beta.www.matching.conversations.CandidateOfferMatch.objects.select_for_update'
        ) as locked:
            locked.return_value.get.side_effect = changed_while_waiting
            self.assertEqual(self.adviser_client.get(self.start).status_code, 404)
