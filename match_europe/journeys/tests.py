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
from journeys.forms import UploadForm
from journeys.models import AccessToken, Answer, Conversation, Match, Message, Offer, Profile
from journeys.services import consume_token, dispatch_offer, invite_for, issue_token


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
        self.assertEqual(self.client.get('/').status_code, 302)



    def test_pdf_validation(self):
        form = UploadForm({'agreement': True}, {'document': SimpleUploadedFile('bad.pdf', b'not a PDF')})
        self.assertFalse(form.is_valid())



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




