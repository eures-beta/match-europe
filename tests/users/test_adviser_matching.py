from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import offer_review_services, services
from eures_beta.matching.models import CandidateOfferReview, CandidateOfferMatch
from tests.matching.test_dialogue import SETTINGS
from eures_beta.users.test_accounts import prepared_user


@override_settings(**{**SETTINGS, 'ALBERT_SIMULATED': True})
class AdviserMatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        cls.adviser = prepared_user('adviser')
        cls.adviser.groups.clear()
        cls.adviser.user_permissions.clear()
        cls.match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        # Exercise the adviser decision before any candidate review is requested.
        CandidateOfferReview.objects.filter(match=cls.match).delete()

    def setUp(self):
        self.client.force_login(self.adviser)
        self.dashboard = reverse('dashboard')
        self.detail = reverse('adviser_match', args=[self.match.pk])
        self.evaluation = services.calculate(self.match.candidate, self.match.offer)

    def decide(self, value):
        return self.client.post(
            self.detail, {'action': value, 'evaluation': self.evaluation.pk}
        )

    def test_validation_opens_candidate_dialogue_and_adviser_followup(self):
        page = self.client.get(self.dashboard, {'lang': 'fr'})
        self.assertContains(page, 'aria-current="page">À traiter')
        self.assertContains(page, self.detail)
        self.assertContains(page, 'value="retained"')
        self.assertContains(page, 'value="refused"')
        self.assertNotContains(page, 'adviser-match-decision')
        self.assertContains(self.client.get(self.detail), 'value="retained"')
        self.assertEqual(self.decide('retained').status_code, 302)
        self.assertNotContains(self.client.get(self.dashboard), self.detail)
        conversation = CandidateOfferReview.objects.get(match=self.match)
        tracking = self.dashboard + '?view=conversations'
        follow = reverse('adviser_conversation', args=[conversation.pk])
        self.assertContains(self.client.get(tracking), follow)
        self.assertEqual(self.client.get(follow).status_code, 200)
        self.assertEqual(self.decide('retained').status_code, 404)
        self.assertEqual(
            CandidateOfferReview.objects.filter(match=self.match).count(), 1
        )

        candidate = Client()
        candidate.force_login(self.match.candidate.user)
        dialogue = reverse('candidate_offer_dialogue', args=[conversation.pk])
        self.assertContains(candidate.get(reverse('candidate_offer_inbox')), dialogue)
        self.assertEqual(candidate.get(dialogue).status_code, 200)
        self.assertEqual(self.match.decisions.get().by_adviser, self.adviser)
        self.assertEqual(candidate.get(follow).status_code, 403)
        self.assertEqual(
            candidate.post(self.detail, {'action': 'refused'}).status_code, 403
        )

        for row in offer_review_services.review_state(conversation)['rows']:
            if row['askable']:
                offer_review_services.answer(
                    self.match.candidate.user,
                    conversation.pk,
                    row['key'],
                    row['fingerprint'],
                    'yes',
                )
        state = offer_review_services.review_state(conversation)
        offer_review_services.agree(
            self.match.candidate.user, conversation.pk, state['fingerprint'], False
        )
        self.assertContains(self.client.get(tracking), follow)
        self.assertEqual(self.client.get(follow).status_code, 200)

    def test_albert_opinion_uses_current_answers_and_never_decides(self):
        self.assertEqual(self.decide('retained').status_code, 302)
        conversation = CandidateOfferReview.objects.get(match=self.match)
        follow = reverse('adviser_conversation', args=[conversation.pk]) + '?lang=fr'
        state = offer_review_services.review_state(conversation)
        self.assertTrue(state['pending'])
        self.assertNotContains(self.client.get(follow), 'Analyser les réponses')
        self.assertEqual(
            self.client.post(
                follow, {'action': 'analyse', 'fingerprint': state['fingerprint']}
            ).status_code,
            409,
        )
        rows = [row for row in state['rows'] if row['askable']]
        first = rows[0]
        for row in rows:
            offer_review_services.answer(
                self.match.candidate.user,
                conversation.pk,
                row['key'],
                row['fingerprint'],
                'yes',
            )
        current = offer_review_services.review_state(conversation)['fingerprint']
        self.assertContains(self.client.get(follow), 'Analyser les réponses')
        with patch('eures_beta.matching.dialogue_albert.complete') as complete:
            page = self.client.post(
                follow, {'action': 'analyse', 'fingerprint': current}
            )
            complete.assert_not_called()
        self.assertContains(page, 'Analyse simulée')
        self.assertContains(self.client.get(follow), 'Analyse simulée')
        self.assertFalse(conversation.profile_sharings.exists())
        self.assertEqual(self.match.decisions.count(), 1)

        previous = conversation.answers.get(question_key=first['key'])
        offer_review_services.answer(
            self.match.candidate.user,
            conversation.pk,
            first['key'],
            first['fingerprint'],
            'conditional',
            'Prévenir trois jours avant.',
            previous=previous.pk,
        )
        self.assertNotContains(self.client.get(follow), 'Analyse simulée')
        self.assertEqual(
            self.client.post(
                follow, {'action': 'analyse', 'fingerprint': current}
            ).status_code,
            409,
        )
        current = offer_review_services.review_state(conversation)['fingerprint']
        page = self.client.post(follow, {'action': 'analyse', 'fingerprint': current})
        self.assertContains(page, 'Demander une précision')

    @override_settings(
        ALBERT_SIMULATED=False,
        ALBERT_API_KEY='fictional-test-key',
    )
    def test_albert_opinion_validates_model_output_before_showing_it(self):
        self.assertEqual(self.decide('retained').status_code, 302)
        conversation = CandidateOfferReview.objects.get(match=self.match)
        follow = reverse('adviser_conversation', args=[conversation.pk]) + '?lang=fr'
        rows = [
            row
            for row in offer_review_services.review_state(conversation)['rows']
            if row['askable']
        ]
        for index, row in enumerate(rows):
            offer_review_services.answer(
                self.match.candidate.user,
                conversation.pk,
                row['key'],
                row['fingerprint'],
                'conditional' if index == 0 else 'yes',
                'Sous réserve de trois jours de préavis.' if index == 0 else '',
            )
        data = {
            'action': 'analyse',
            'fingerprint': offer_review_services.review_state(conversation)[
                'fingerprint'
            ],
        }
        point = {
            'condition': str(
                next(
                    i
                    for i, row in enumerate(
                        offer_review_services.review_state(conversation)['rows'], 1
                    )
                    if row['askable']
                )
            ),
            'reason': 'Le candidat demande trois jours de préavis.',
            'question': 'L’employeur peut-il donner trois jours de préavis ?',
        }
        with patch(
            'eures_beta.matching.dialogue_albert.complete',
            side_effect=[
                {'recommendation': 'proceed', 'points': [point]},
                {'recommendation': 'clarify', 'points': [point]},
            ],
        ) as complete:
            self.assertEqual(self.client.post(follow, data).status_code, 503)
            self.assertContains(self.client.post(follow, data), point['question'])
            payload = complete.call_args.args[1]
            self.assertEqual(
                payload['conditions'][point['condition']]['answer'], 'conditional'
            )
            self.assertNotIn(self.match.candidate.user.email, str(payload))
        self.assertFalse(conversation.profile_sharings.exists())

    def test_refusal_closes_matching_without_opening_dialogue(self):
        self.assertEqual(self.decide('refused').status_code, 302)
        self.match.refresh_from_db()
        self.assertEqual(self.match.decision, 'refused')
        self.assertFalse(CandidateOfferReview.objects.filter(match=self.match).exists())
        self.assertNotContains(self.client.get(self.dashboard), self.detail)

    def test_stale_evaluation_requires_review_again(self):
        services.calculate(self.match.candidate, self.match.offer)
        self.assertEqual(self.decide('retained').status_code, 409)
        self.assertFalse(CandidateOfferReview.objects.filter(match=self.match).exists())

    @override_settings(ALBERT_SIMULATED=False, ALBERT_API_KEY='')
    def test_unavailable_albert_keeps_matching_pending(self):
        self.assertEqual(self.decide('retained').status_code, 400)
        self.match.refresh_from_db()
        self.assertEqual(self.match.decision, 'pending')
        self.assertFalse(CandidateOfferReview.objects.filter(match=self.match).exists())
