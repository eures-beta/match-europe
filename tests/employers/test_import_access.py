from urllib.parse import urlencode
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from sesame.utils import get_query_string

from eures_beta.employers.models import JobOffer

User = get_user_model()


class ImportAccessTests(TestCase):
    destination = '/employer/pages/import-fr.html'

    def setUp(self):
        self.employer = User.objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        self.adviser = User.objects.create_user(
            email='adviser@example.invalid', kind='adviser'
        )

    def test_landing_remains_public_but_import_requires_employer(self):
        for language in ('fr', 'en', 'de'):
            self.assertContains(
                self.client.get(f'/employer/pages/{language}.html', secure=True),
                'import-' + language + '.html',
            )
            for prefix in ('import-',):
                path = f'/employer/pages/{prefix}{language}.html'
                for user in (None, self.adviser):
                    if user:
                        self.client.force_login(user)
                    page = self.client.get(path, secure=True)
                    self.assertTemplateUsed(page, 'employer/import_access.html')
                    self.assertNotContains(page, 'id="file-form"')
                    self.assertContains(page, '<html lang="' + language + '">')
                    self.client.logout()
                self.client.force_login(self.employer)
                page = self.client.get(path, secure=True)
                self.assertContains(page, 'data-employer-connected="true"')
                self.assertContains(page, 'id="file-form"')
                self.client.logout()

    @patch('eures_beta.www.employer.imports.read_url')
    def test_direct_api_cannot_bypass_gate_or_start_extraction(self, reader):
        for user in (None, self.adviser):
            if user:
                self.client.force_login(user)
            for url in ('/api/imports/', '/api/imports/source/'):
                response = self.client.post(
                    url,
                    {
                        'kind': 'url',
                        'agreement': 'true',
                        'url': 'https://example.invalid',
                    },
                    secure=True,
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()['error'], 'employer_account_required')
            self.assertEqual(
                self.client.get('/api/imports/', secure=True).status_code, 403
            )
        reader.assert_not_called()
        self.assertFalse(JobOffer.objects.exists())

    def test_access_page_language_selector_updates_the_resume_destination(self):
        response = self.client.get(self.destination, {'lang': 'de'}, secure=True)
        self.assertContains(response, 'Ein Arbeitgeberkonto ist erforderlich')
        self.assertContains(response, '<html lang="de">')
        self.assertEqual(
            self.client.session['login_return_path'], '/employer/pages/import-de.html'
        )

    @patch('eures_beta.www.employer.imports.aglae')
    def test_saved_offer_is_owned_by_authenticated_account_not_submitted_email(
        self, external
    ):
        self.client.force_login(self.employer)
        response = self.client.post(
            '/api/imports/',
            {
                'kind': 'manual',
                'agreement': 'true',
                'text': 'Fictional job',
                'email': self.adviser.email,
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'contact@example.invalid'}
                ),
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 201)
        offer = JobOffer.objects.get()
        self.assertEqual(offer.created_by, self.employer)
        self.assertEqual(offer.email, self.employer.email)
        self.assertEqual(offer.session_key, '')
        self.assertEqual(response.json()['login_url'], reverse('dashboard'))
        self.assertContains(
            self.client.get(reverse('dashboard')),
            'Fictional job' if offer.data.get('title') else 'Offre sans intitulé',
        )
        external.assert_not_called()
        other = User.objects.create_user(email='other@example.invalid', kind='employer')
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(f'/api/imports/{offer.pk}/', secure=True).status_code, 404
        )

    def test_magic_link_resumes_allowlisted_import_even_after_account_switch(self):
        self.client.force_login(self.adviser)
        self.client.get(self.destination, secure=True)
        link = reverse('magic_confirm') + get_query_string(self.employer)
        self.client.get(link, secure=True)
        response = self.client.post(reverse('magic_confirm'), secure=True)
        self.assertRedirects(response, self.destination, fetch_redirect_response=False)
        self.assertContains(
            self.client.get(self.destination, secure=True),
            'data-employer-connected="true"',
        )

    def test_magic_link_in_new_browser_accepts_only_fixed_local_import_destinations(
        self,
    ):
        for destination in (
            self.destination,
            'https://attacker.invalid',
            '//attacker.invalid',
            '/admin/',
        ):
            self.employer.refresh_from_db()
            client = Client()
            client.get(
                reverse('magic_confirm')
                + get_query_string(self.employer)
                + '&'
                + urlencode({'next': destination}),
                secure=True,
            )
            response = client.post(reverse('magic_confirm'), secure=True)
            self.assertEqual(
                response['Location'],
                (
                    self.destination
                    if destination == self.destination
                    else reverse('dashboard')
                ),
            )

    @override_settings(
        TEST_ACCOUNTS_ENABLED=True,
        DJANGO_ENVIRONMENT='preview',
        EMAIL_DELIVERY_ENABLED=False,
    )
    def test_instant_test_login_resumes_import(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_test_accounts', stdout=StringIO())
        self.client.get(self.destination, secure=True)
        response = self.client.post(
            reverse('test_account_sign_in'), {'account': 'employer'}, secure=True
        )
        self.assertEqual(response['Location'], self.destination)

    def test_wrong_role_can_sign_out_and_resume_without_creating_an_account(self):
        self.client.force_login(self.adviser)
        page = self.client.get(self.destination, secure=True)
        self.assertContains(page, reverse('magic_logout'))
        response = self.client.post(
            reverse('magic_logout') + '?next=' + self.destination, secure=True
        )
        self.assertTrue(
            response['Location'].startswith(reverse('magic_login') + '?next=')
        )
        self.assertIn('lang=fr', response['Location'])
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(User.objects.count(), 2)

    @patch('eures_beta.www.employer.imports.read_url')
    def test_source_cannot_be_reused_by_another_account_in_the_same_browser(
        self, reader
    ):
        reader.return_value = (
            {'description': 'Fictional source'},
            'https://example.invalid/job',
        )
        self.client.force_login(self.employer)
        response = self.client.post(
            '/api/imports/source/',
            {'agreement': 'true', 'kind': 'url', 'url': 'https://example.invalid/job'},
            secure=True,
        )
        pending = dict(self.client.session['pending_offer_source'])
        other = User.objects.create_user(
            email='second@example.invalid', kind='employer'
        )
        self.client.force_login(other)
        session = self.client.session
        session['pending_offer_source'] = pending
        session.save()
        response = self.client.post(
            '/api/imports/',
            {
                'agreement': 'true',
                'kind': 'url',
                'url': 'https://example.invalid/job',
                'sourceToken': response.json()['token'],
                'contact': json.dumps(
                    {'name': 'Test', 'email': 'test@example.invalid'}
                ),
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(JobOffer.objects.exists())

    @patch('eures_beta.www.accounts.views.send_mail')
    @patch('eures_beta.www.accounts.views.email_ready', return_value=True)
    @override_settings(
        LOGIN_EMAIL_ORIGIN='https://testserver',
        DEFAULT_FROM_EMAIL='sender@example.invalid',
    )
    def test_requested_magic_email_carries_only_allowed_return_path(self, ready, send):
        self.client.get(reverse('magic_login'), {'next': self.destination}, secure=True)
        self.client.post(
            reverse('magic_login'), {'email': self.employer.email}, secure=True
        )
        self.assertEqual(send.call_count, 1)
        self.assertIn(
            'next=%2Femployer%2Fpages%2Fimport-fr.html', send.call_args.args[1]
        )

    def test_invitation_help_points_to_an_eures_adviser(self):
        for language in ('fr', 'en', 'de'):
            link = 'mailto:eric.barthelemy@francetravail.fr'
            for path in (
                f'/employer/pages/{language}.html',
                f'/employer/pages/import-{language}.html',
                f'/accounts/login/?lang={language}',
            ):
                with self.subTest(path=path):
                    page = self.client.get(path, secure=True)
                    self.assertContains(page, 'Eric Barthélémy')
                    self.assertNotContains(page, 'search-for-advisers')
                    self.assertContains(page, 'href="' + link + '"')
        self.client.force_login(self.employer)
        self.assertNotContains(
            self.client.get('/employer/pages/fr.html', secure=True),
            'employer-invitation-help',
        )

    @override_settings(
        EMPLOYER_ADVISER_CONTACT_URL='https://contact.example.invalid/?x=1'
    )
    def test_configured_adviser_contact_is_used_as_is(self):
        page = self.client.get('/employer/pages/import-en.html', secure=True)
        self.assertContains(page, 'href="https://contact.example.invalid/?x=1"')

    def test_signed_in_employer_contact_email_is_prefilled(self):
        self.client.force_login(self.employer)
        page = self.client.get(self.destination, secure=True)
        self.assertContains(page, 'data-employer-email="employer@example.invalid"')
        self.client.logout()
        self.assertNotContains(
            self.client.get('/employer/pages/fr.html', secure=True),
            'data-employer-email',
        )
