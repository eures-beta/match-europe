from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from eures_beta.accounts.models import AccessToken
from eures_beta.accounts.services import consume_token, invite_for, issue_token


from eures_beta.testing_support import DomainScenario


class AccessTests(DomainScenario):
    def test_tokens_expire_are_single_use_and_get_does_not_consume(self):
        raw = issue_token(self.users['employer'])
        self.assertEqual(
            self.client.get(reverse('confirm', args=[raw])).status_code, 200
        )
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
        self.assertEqual(
            client.post(
                reverse('match', args=[self.match.pk]), {'action': 'invite'}
            ).status_code,
            403,
        )

    def test_invitation_creates_only_draft_access_not_verified_identity(self):
        token = invite_for(self.users['adviser'])
        url = reverse('access') + '?role=employer&invite=' + token
        self.client.get(url)
        self.client.post(url, {'email': 'new@example.invalid'})
        person = User.objects.get(username='new@example.invalid')
        self.assertFalse(person.profile.verified)
        self.assertEqual(person.profile.adviser_id, self.users['adviser'].pk)
        self.assertEqual(self.client.get(reverse('upload')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404
        )

    def test_existing_email_does_not_grant_draft_access(self):
        url = (
            reverse('access')
            + '?role=employer&invite='
            + invite_for(self.users['adviser'])
        )
        self.client.get(url)
        self.client.post(url, {'email': self.users['employer'].email})
        self.assertNotIn('draft_user', self.client.session)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)
