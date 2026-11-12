from io import StringIO

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import confirmation_services, services
from eures_beta.matching.models import ConfirmationRequest, MatchPair
from eures_beta.matching.tests.test_dialogue import SETTINGS
from eures_beta.users.test_accounts import prepared_user


@override_settings(**{**SETTINGS, 'CONFIRMATION_DIALOGUE_SIMULATED': True})
class AdviserMatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        cls.adviser = prepared_user('adviser')
        cls.adviser.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label='matching',
                codename__in=('view_matchpair', 'change_matchpair'),
            )
        )
        cls.pair = MatchPair.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )

    def setUp(self):
        self.client.force_login(self.adviser)
        self.dashboard = reverse('dashboard')
        self.detail = reverse('adviser_match', args=[self.pair.pk])
        self.evaluation = services.calculate(self.pair.candidate, self.pair.offer)

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
        conversation = ConfirmationRequest.objects.get(pair=self.pair)
        tracking = self.dashboard + '?view=conversations'
        follow = reverse('adviser_conversation', args=[conversation.pk])
        self.assertContains(self.client.get(tracking), follow)
        self.assertEqual(self.client.get(follow).status_code, 200)
        self.assertEqual(self.decide('retained').status_code, 404)
        self.assertEqual(ConfirmationRequest.objects.filter(pair=self.pair).count(), 1)

        candidate = Client()
        candidate.force_login(self.pair.candidate.user)
        dialogue = reverse('candidate_offer_dialogue', args=[conversation.pk])
        self.assertContains(candidate.get(reverse('candidate_offer_inbox')), dialogue)
        self.assertEqual(candidate.get(dialogue).status_code, 200)
        self.assertEqual(self.pair.decisions.get().actor, f'adviser:{self.adviser.pk}')
        self.assertEqual(candidate.get(follow).status_code, 403)
        self.assertEqual(
            candidate.post(self.detail, {'action': 'refused'}).status_code, 403
        )

        for row in confirmation_services.review(conversation)['rows']:
            if row['askable']:
                confirmation_services.answer(
                    self.pair.candidate.user,
                    conversation.pk,
                    row['key'],
                    row['fingerprint'],
                    'yes',
                )
        state = confirmation_services.review(conversation)
        confirmation_services.agree(
            self.pair.candidate.user, conversation.pk, state['fingerprint'], False
        )
        self.assertNotContains(self.client.get(tracking), follow)
        self.assertEqual(self.client.get(follow).status_code, 404)

    def test_refusal_closes_matching_without_opening_dialogue(self):
        self.assertEqual(self.decide('refused').status_code, 302)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.decision, 'refused')
        self.assertFalse(ConfirmationRequest.objects.filter(pair=self.pair).exists())
        self.assertNotContains(self.client.get(self.dashboard), self.detail)

    def test_stale_evaluation_requires_review_again(self):
        services.calculate(self.pair.candidate, self.pair.offer)
        self.assertEqual(self.decide('retained').status_code, 409)
        self.assertFalse(ConfirmationRequest.objects.filter(pair=self.pair).exists())

    @override_settings(
        CONFIRMATION_DIALOGUE_SIMULATED=False, CONFIRMATION_DIALOGUE_ENABLED=False
    )
    def test_unavailable_albert_keeps_matching_pending(self):
        self.assertEqual(self.decide('retained').status_code, 400)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.decision, 'pending')
        self.assertFalse(ConfirmationRequest.objects.filter(pair=self.pair).exists())
