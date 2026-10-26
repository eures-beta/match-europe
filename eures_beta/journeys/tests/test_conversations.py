from django.urls import reverse
from eures_beta.journeys.models import Answer
from eures_beta.conversations.models import Conversation, Message


from .base import JourneyScenario


class ConversationsTests(JourneyScenario):
    def test_complete_introduction_and_three_party_messages(self):
        self.as_role('adviser')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'invite'})
        self.as_role('candidate')
        self.client.post(
            reverse('match', args=[self.match.pk]), {'action': 'interested'}
        )
        payload = {'action': 'submit_answers', 'agreement': 'yes'}
        for question in self.offer.questions.all():
            payload[f'text_{question.pk}'] = 'Réponse libre avec une nuance à examiner.'
        self.client.post(reverse('match', args=[self.match.pk]), payload)
        self.assertEqual(Answer.objects.count(), self.offer.questions.count())
        self.as_role('adviser')
        self.client.post(
            reverse('match', args=[self.match.pk]),
            {'action': 'introduce', 'note': 'Présentation'},
        )
        self.assertFalse(Conversation.objects.exists())
        self.as_role('employer')
        self.client.post(
            reverse('match', args=[self.match.pk]),
            {'action': 'employer_agree', 'agreement': 'yes'},
        )
        self.as_role('adviser')
        self.client.post(
            reverse('match', args=[self.match.pk]),
            {'action': 'introduce', 'note': 'Bienvenue à vous deux.'},
        )
        conv = Conversation.objects.get()
        for role in ['candidate', 'employer', 'adviser']:
            self.as_role(role)
            self.assertEqual(
                self.client.post(
                    reverse('conversation', args=[conv.pk]), {'body': f'Message {role}'}
                ).status_code,
                302,
            )
            self.assertEqual(
                self.client.get(reverse('conversation', args=[conv.pk])).status_code,
                200,
            )
        self.assertEqual(Message.objects.count(), 4)
        self.as_role('admin')
        self.assertEqual(
            self.client.get(reverse('conversation', args=[conv.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse('conversation_feed', args=[conv.pk])).status_code,
            404,
        )

    def test_admin_cannot_initiate_private_conversation(self):
        self.match.state = 'review'
        self.match.candidate_agreement = True
        self.match.employer_agreement = True
        self.match.save()
        self.as_role('admin')
        self.assertEqual(
            self.client.post(
                reverse('match', args=[self.match.pk]),
                {'action': 'introduce', 'note': 'No'},
            ).status_code,
            404,
        )
        self.assertFalse(Conversation.objects.exists())

    def test_message_html_is_escaped(self):
        conv = Conversation.objects.create(
            match=self.match, opened_by=self.users['adviser']
        )
        Message.objects.create(
            conversation=conv,
            sender=self.users['candidate'],
            body='<script>alert(1)</script>',
        )
        self.as_role('employer')
        response = self.client.get(reverse('conversation', args=[conv.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
