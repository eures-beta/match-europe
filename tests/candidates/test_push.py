from unittest.mock import patch
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from eures_beta.candidates import push
from eures_beta.candidates.models import CandidatePushSubscription
from eures_beta.users.test_accounts import prepared_user


@override_settings(SECRET_KEY='fictional-push-rotation-test')
class PushKeyTests(SimpleTestCase):
    def test_new_key_is_stable_and_differs_from_the_previous_context(self):
        current = push.public_key()
        self.assertEqual(current, push.public_key())
        self.assertEqual(push.KEY_DERIVATION_CONTEXT, b'match-europe-push-v1')
        with patch.object(
            push, 'KEY_DERIVATION_CONTEXT', b'match-europe-preview-push-v1'
        ):
            self.assertNotEqual(current, push.public_key())

    @override_settings(SECRET_KEY='another-fictional-push-rotation-test')
    def test_distinct_application_secrets_produce_distinct_push_keys(self):
        current = push.public_key()
        with self.settings(SECRET_KEY='fictional-push-rotation-test'):
            self.assertNotEqual(current, push.public_key())


@override_settings(
    DJANGO_ENVIRONMENT='local',
    DEMO_ACCOUNTS_ENABLED=True,
    EMAIL_DELIVERY_ENABLED=False,
)
class PushProfileTests(TestCase):
    def test_profile_only_exposes_the_connected_candidates_endpoint(self):
        call_command('seed_test_accounts', stdout=StringIO())
        owner = prepared_user('candidate-pwa')
        other = prepared_user('candidate-pwa-replay')
        for user, name in ((owner, 'owner'), (other, 'other')):
            CandidatePushSubscription.objects.create(
                candidate=user.candidate_profile,
                endpoint=f'https://web.push.apple.com/fictional-{name}',
                keys={'p256dh': 'fictional-public', 'auth': 'fictional-auth'},
            )
        self.client.force_login(owner)
        response = self.client.get(reverse('candidate_profile'))
        self.assertTemplateUsed(response, 'candidates/pwa_profile.html')
        self.assertContains(response, 'https://web.push.apple.com/fictional-owner')
        self.assertNotContains(response, 'https://web.push.apple.com/fictional-other')
