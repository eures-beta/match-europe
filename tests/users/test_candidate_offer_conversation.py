from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import offer_review_services, services
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
        call_command('seed_test_accounts', stdout=StringIO())
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
        cls.employer = cls.match.offer.created_by

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
        self.assertFalse(self.review.profile_sharings.exists())
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
