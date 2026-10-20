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



    def test_existing_email_does_not_grant_draft_access(self):
        url = reverse('access') + '?role=employer&invite=' + invite_for(self.users['adviser'])
        self.client.get(url)
        self.client.post(url, {'email': self.users['employer'].email})
        self.assertNotIn('draft_user', self.client.session)
        self.assertEqual(self.client.get('/').status_code, 302)










