from django.urls import reverse
from eures_beta.journeys.models import Answer


from eures_beta.journeys.tests.base import JourneyScenario


class MatchingTests(JourneyScenario):
    def test_answers_preserve_choice_and_free_text_without_rejection(self):
        self.match.state = 'answering'
        self.match.save()
        self.as_role('candidate')
        q = self.offer.questions.first()
        self.client.post(
            reverse('match', args=[self.match.pk]),
            {
                'action': 'save_answers',
                f'choice_{q.pk}': q.choices()[0],
                f'text_{q.pk}': 'Sauf le mercredi',
            },
        )
        answer = Answer.objects.get(question=q)
        self.assertEqual(answer.choice, q.choices()[0])
        self.assertEqual(answer.text, 'Sauf le mercredi')
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, 'answering')

    def test_forged_quick_answer_is_rejected(self):
        self.match.state = 'answering'
        self.match.save()
        self.as_role('candidate')
        q = self.offer.questions.first()
        response = self.client.post(
            reverse('match', args=[self.match.pk]),
            {'action': 'save_answers', f'choice_{q.pk}': 'forged'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Answer.objects.exists())

    def test_candidate_profile_incomplete_draft_then_validation(self):
        person = self.users['candidate']
        profile = person.candidate
        profile.sent_at = None
        profile.validated_at = None
        profile.save()
        self.as_role('candidate')
        self.client.post(
            reverse('candidate_edit'), {'action': 'save', 'name': 'Prénom fictif'}
        )
        profile.refresh_from_db()
        self.assertEqual(profile.name, 'Prénom fictif')
        self.assertIsNone(profile.sent_at)
        self.client.post(
            reverse('candidate_edit'),
            {'action': 'validate', 'agreement': 'yes', 'name': 'Prénom fictif'},
        )
        profile.refresh_from_db()
        self.assertIsNone(profile.validated_at)

    def test_partial_answers_are_not_visible_to_adviser(self):
        self.match.state = 'answering'
        self.match.save()
        Answer.objects.create(
            match=self.match,
            question=self.offer.questions.first(),
            text='PRIVATE_DRAFT_TEXT',
        )
        self.as_role('adviser')
        response = self.client.get(reverse('match', args=[self.match.pk]))
        self.assertNotContains(response, 'PRIVATE_DRAFT_TEXT')
