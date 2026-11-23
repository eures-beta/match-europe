from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DJANGO_ENVIRONMENT='preview',
    DEMO_ACCOUNTS_ENABLED=True,
    EMAIL_DELIVERY_ENABLED=False,
)
class DemoBannerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())

    @patch('eures_beta.candidates.push.available', return_value=True)
    @patch('eures_beta.candidates.push.public_key', return_value='fictional-push-key')
    def test_candidate_push_profile_and_selector_keep_the_demo_banner(self, *mocks):
        self.client.force_login(prepared_user('candidate-pwa'))
        for language in ('fr', 'en', 'de'):
            for route in ('candidate_profile', 'test_accounts'):
                with self.subTest(language=language, route=route):
                    response = self.client.get(reverse(route), {'lang': language})
                    self.assertContains(
                        response, 'class="test-accounts-banner"', count=1
                    )
                    self.assertContains(response, 'users/test_accounts.css')
                    self.assertContains(response, f'?lang={language}')
                    if route == 'candidate_profile':
                        self.assertTemplateUsed(response, 'candidates/pwa_profile.html')

    @override_settings(DEMO_ACCOUNTS_ENABLED=False, DJANGO_ENVIRONMENT='production')
    @patch('eures_beta.candidates.push.available', return_value=True)
    @patch('eures_beta.candidates.push.public_key', return_value='fictional-push-key')
    def test_production_profile_has_no_demo_banner_or_demo_styles(self, *mocks):
        self.client.force_login(prepared_user('candidate-pwa'))
        response = self.client.get(reverse('candidate_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="test-accounts-banner"')
        self.assertNotContains(response, 'users/test_accounts.css')
