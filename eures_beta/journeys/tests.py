from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
import tempfile
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from eures_beta.journeys.forms import UploadForm
from eures_beta.journeys.models import AccessToken, Answer, Conversation, Match, Message, Offer, Profile
from eures_beta.journeys.services import consume_token, dispatch_offer, invite_for, issue_token


class JourneysTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.users = {role: User.objects.get(profile__role=role) for role in ['adviser', 'employer', 'candidate', 'admin']}
        self.match = Match.objects.get()
        self.offer = self.match.offer

    def as_role(self, role):
        self.client.force_login(self.users[role])

    def test_complete_introduction_and_three_party_messages(self):
        self.as_role('adviser')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'invite'})
        self.as_role('candidate')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'interested'})
        payload = {'action': 'submit_answers', 'agreement': 'yes'}
        for question in self.offer.questions.all():
            payload[f'text_{question.pk}'] = 'Réponse libre avec une nuance à examiner.'
        self.client.post(reverse('match', args=[self.match.pk]), payload)
        self.assertEqual(Answer.objects.count(), self.offer.questions.count())
        self.as_role('adviser')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'introduce', 'note': 'Présentation'})
        self.assertFalse(Conversation.objects.exists())
        self.as_role('employer')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'employer_agree', 'agreement': 'yes'})
        self.as_role('adviser')
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'introduce', 'note': 'Bienvenue à vous deux.'})
        conv = Conversation.objects.get()
        for role in ['candidate', 'employer', 'adviser']:
            self.as_role(role)
            self.assertEqual(self.client.post(reverse('conversation', args=[conv.pk]), {'body': f'Message {role}'}).status_code, 302)
            self.assertEqual(self.client.get(reverse('conversation', args=[conv.pk])).status_code, 200)
        self.assertEqual(Message.objects.count(), 4)
        self.as_role('admin')
        self.assertEqual(self.client.get(reverse('conversation', args=[conv.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('conversation_feed', args=[conv.pk])).status_code, 404)

    def test_offer_and_match_object_permissions(self):
        outsider = User.objects.create_user('other@example.invalid')
        Profile.objects.create(user=outsider, role='employer', verified=True)
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('offer', args=[self.offer.pk]), {'action': 'suggest'}).status_code, 404)
        self.as_role('candidate')
        self.assertEqual(self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('match', args=[self.match.pk])).status_code, 404)
        self.as_role('employer')
        self.assertEqual(self.client.get(reverse('match', args=[self.match.pk])).status_code, 404)

    def test_employer_cannot_trigger_suggestions_or_change_validated_offer(self):
        self.as_role('employer')
        for action in ['suggest', 'validate', 'question']:
            self.assertEqual(self.client.post(reverse('offer', args=[self.offer.pk]), {'action': action}).status_code, 404)

    def test_no_dispatch_before_validation_and_email_confirmation(self):
        self.offer.sent_at = None
        self.offer.validated_at = None
        with self.assertRaises(ValueError):
            dispatch_offer(self.offer, self.users['employer'])
        self.offer.validated_at = timezone.now()
        Profile.objects.filter(user=self.users['employer']).update(verified=False)
        self.offer.employer.refresh_from_db()
        with self.assertRaises(ValueError):
            dispatch_offer(self.offer, self.users['employer'])

    def test_tokens_expire_are_single_use_and_get_does_not_consume(self):
        raw = issue_token(self.users['employer'])
        self.assertEqual(self.client.get(reverse('confirm', args=[raw])).status_code, 200)
        self.assertFalse(AccessToken.objects.get().used)
        self.assertIsNotNone(consume_token(raw))
        self.assertIsNone(consume_token(raw))
        self.assertIsNone(issue_token(self.users['employer']))
        AccessToken.objects.all().delete()
        raw = issue_token(self.users['candidate'])
        AccessToken.objects.update(expires=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(consume_token(raw))

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users['adviser'])
        self.assertEqual(client.post(reverse('match', args=[self.match.pk]), {'action': 'invite'}).status_code, 403)

    def test_invitation_creates_only_draft_access_not_verified_identity(self):
        token = invite_for(self.users['adviser'])
        url = reverse('access') + '?role=employer&invite=' + token
        self.client.get(url)
        self.client.post(url, {'email': 'new@example.invalid'})
        person = User.objects.get(username='new@example.invalid')
        self.assertFalse(person.profile.verified)
        self.assertEqual(person.profile.adviser_id, self.users['adviser'].pk)
        self.assertEqual(self.client.get(reverse('upload')).status_code, 200)
        self.assertEqual(self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404)

    def test_existing_email_does_not_grant_draft_access(self):
        url = reverse('access') + '?role=employer&invite=' + invite_for(self.users['adviser'])
        self.client.get(url)
        self.client.post(url, {'email': self.users['employer'].email})
        self.assertNotIn('draft_user', self.client.session)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_answers_preserve_choice_and_free_text_without_rejection(self):
        self.match.state = 'answering'
        self.match.save()
        self.as_role('candidate')
        q = self.offer.questions.first()
        self.client.post(reverse('match', args=[self.match.pk]), {'action': 'save_answers', f'choice_{q.pk}': q.choices()[0], f'text_{q.pk}': 'Sauf le mercredi'})
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
        response = self.client.post(reverse('match', args=[self.match.pk]), {'action': 'save_answers', f'choice_{q.pk}': 'forged'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Answer.objects.exists())

    def test_pdf_validation(self):
        form = UploadForm({'agreement': True}, {'document': SimpleUploadedFile('bad.pdf', b'not a PDF')})
        self.assertFalse(form.is_valid())

    def test_three_languages_and_no_private_cache(self):
        self.as_role('adviser')
        for lang, expected in [('fr', 'Mon espace'), ('en', 'My workspace'), ('de', 'Mein Bereich')]:
            self.client.cookies['django_language'] = lang
            response = self.client.get(reverse('dashboard'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response.headers['Cache-Control'])
            self.assertContains(response, expected)
            self.assertContains(response, f'<html lang="{lang}">')

    def test_demo_adapter_never_calls_network(self):
        with patch('socket.create_connection', side_effect=AssertionError('Network forbidden')):
            call_command('seed_demo', verbosity=0)
            self.as_role('adviser')
            self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_employer_pdf_draft_questions_and_validation(self):
        from pypdf import PdfWriter
        self.as_role('employer')
        content = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.write(content)
        response = self.client.post(reverse('upload'), {'agreement': 'yes', 'document': SimpleUploadedFile('fiction.pdf', content.getvalue())})
        self.assertEqual(response.status_code, 302)
        obj = Offer.objects.exclude(pk=self.offer.pk).get()
        self.assertEqual(obj.state, 'draft')
        self.assertFalse(obj.sent_at)
        self.assertEqual(self.client.get(reverse('offer', args=[obj.pk])).status_code, 200)
        self.client.post(reverse('offer', args=[obj.pk]), {'action': 'save', 'title': 'Brouillon incomplet'})
        obj.refresh_from_db()
        self.assertEqual(obj.title, 'Brouillon incomplet')
        self.client.post(reverse('offer', args=[obj.pk]), {'action': 'question', 'text': 'Quand êtes-vous disponible ?', 'options': 'Lundi|À discuter'})
        self.assertEqual(obj.questions.count(), 1)
        self.client.post(reverse('offer', args=[obj.pk]), {'action': 'validate', 'agreement': 'yes', 'title': 'Brouillon incomplet'})
        obj.refresh_from_db()
        self.assertEqual(obj.state, 'draft')
        fields = {'action': 'validate', 'agreement': 'yes', 'title': 'Poste fictif', 'company': 'Société fictive',
                  'location': 'Bruxelles', 'description': 'Description fictive détaillée', 'cross_border': 'yes', 'relocation': 'discuss'}
        self.client.post(reverse('offer', args=[obj.pk]), fields)
        obj.refresh_from_db()
        self.assertEqual(obj.state, 'synced')
        self.assertIsNotNone(obj.sent_at)
        self.assertEqual(Match.objects.filter(offer=obj).count(), 0)

    def test_candidate_profile_incomplete_draft_then_validation(self):
        person = self.users['candidate']
        profile = person.candidate
        profile.sent_at = None
        profile.validated_at = None
        profile.save()
        self.as_role('candidate')
        self.client.post(reverse('candidate_edit'), {'action': 'save', 'name': 'Prénom fictif'})
        profile.refresh_from_db()
        self.assertEqual(profile.name, 'Prénom fictif')
        self.assertIsNone(profile.sent_at)
        self.client.post(reverse('candidate_edit'), {'action': 'validate', 'agreement': 'yes', 'name': 'Prénom fictif'})
        profile.refresh_from_db()
        self.assertIsNone(profile.validated_at)

    def test_partial_answers_are_not_visible_to_adviser(self):
        self.match.state = 'answering'
        self.match.save()
        Answer.objects.create(match=self.match, question=self.offer.questions.first(), text='PRIVATE_DRAFT_TEXT')
        self.as_role('adviser')
        response = self.client.get(reverse('match', args=[self.match.pk]))
        self.assertNotContains(response, 'PRIVATE_DRAFT_TEXT')

    def test_admin_cannot_initiate_private_conversation(self):
        self.match.state = 'review'
        self.match.candidate_agreement = True
        self.match.employer_agreement = True
        self.match.save()
        self.as_role('admin')
        self.assertEqual(self.client.post(reverse('match', args=[self.match.pk]), {'action': 'introduce', 'note': 'No'}).status_code, 404)
        self.assertFalse(Conversation.objects.exists())

    def test_message_html_is_escaped(self):
        conv = Conversation.objects.create(match=self.match, opened_by=self.users['adviser'])
        Message.objects.create(conversation=conv, sender=self.users['candidate'], body='<script>alert(1)</script>')
        self.as_role('employer')
        response = self.client.get(reverse('conversation', args=[conv.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
