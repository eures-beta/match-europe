from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class EmployerRouteTests(TestCase):
    def setUp(self):
        self.employer = get_user_model().objects.create_user(
            email='routes@example.invalid', kind='employer'
        )

    def test_public_landing_and_import_share_canonical_urls_in_all_languages(self):
        for language in ('fr', 'en', 'de'):
            self.client.cookies['django_language'] = 'de' if language != 'de' else 'fr'
            for name, template in (
                ('employer_landing', 'landing.html'),
                ('employer_import', 'import_access.html'),
                ('employer_privacy', 'privacy.html'),
            ):
                with self.subTest(language=language, name=name):
                    response = self.client.get(reverse(name), {'lang': language})
                    self.assertTemplateUsed(response, 'employer/' + template)
                    self.assertContains(response, f'<html lang="{language}"')
                    self.assertNotContains(response, '/employer/pages/')
                    self.assertNotContains(response, 'href="import-')
                    self.assertNotContains(response, 'href="privacy-')

    def test_cookie_selects_language_when_no_query_is_provided(self):
        self.client.cookies['django_language'] = 'de'
        self.assertContains(self.client.get('/employer/'), '<html lang="de"')

    def test_import_keeps_employer_gate_and_prefilled_identity(self):
        self.client.force_login(self.employer)
        response = self.client.get('/employer/import/?lang=en')
        self.assertTemplateUsed(response, 'employer/import.html')
        self.assertContains(response, 'data-employer-connected="true"')
        self.assertContains(response, 'data-employer-email="routes@example.invalid"')

    def test_old_language_pages_redirect_directly_to_canonical_pages(self):
        for folder in ('/employer/pages/', '/previews/employer-landing/'):
            for prefix, target in (
                ('', '/employer/'),
                ('import-', '/employer/import/'),
                ('import-v2-', '/employer/import/'),
                ('privacy-', '/employer/privacy/'),
            ):
                for language in ('fr', 'en', 'de'):
                    with self.subTest(folder=folder, prefix=prefix, language=language):
                        response = self.client.get(
                            f'{folder}{prefix}{language}.html?source=bookmark&offer=one'
                        )
                        self.assertEqual(response.status_code, 301)
                        destination = urlsplit(response['Location'])
                        self.assertEqual(destination.path, target)
                        self.assertEqual(
                            parse_qs(destination.query),
                            {
                                'lang': [language],
                                'source': ['bookmark'],
                                'offer': ['one'],
                            },
                        )

    def test_explicit_query_language_takes_priority_for_an_old_bookmark(self):
        self.assertRedirects(
            self.client.get('/employer/pages/fr.html?lang=de'),
            '/employer/?lang=de',
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_legacy_pages_never_accept_writes_or_expose_template_fragments(self):
        self.client.force_login(self.employer)
        for fragment in (
            'landing.html',
            'import.html',
            'condition_strings.html',
            '../base.html',
        ):
            self.assertEqual(
                self.client.get('/employer/pages/' + fragment).status_code, 404
            )
        self.assertEqual(
            self.client.post('/employer/pages/import-fr.html').status_code, 405
        )
        self.assertEqual(self.client.post('/employer/').status_code, 405)
        self.assertEqual(self.client.post('/employer/import/').status_code, 405)

    def test_connected_is_only_a_retired_bookmark_redirect(self):
        self.assertRedirects(
            self.client.get('/employer/connected/?lang=de'),
            '/employer/offers/?lang=de',
            status_code=301,
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.post('/employer/connected/').status_code, 405)

    def test_old_api_preserves_method_and_body_for_cached_javascript(self):
        # A 301/302 would silently turn a cached browser's POST into a GET.
        for suffix in ('', 'source/', '00000000-0000-0000-0000-000000000001/'):
            response = self.client.post('/api/imports/' + suffix, {'kind': 'manual'})
            self.assertEqual(response.status_code, 308)
            self.assertEqual(response['Location'], '/api/job-offers/' + suffix)
        refused = Client().post('/api/job-offers/', {'kind': 'manual'})
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json()['error'], 'employer_account_required')

    @patch('eures_beta.www.employer.imports.read_url')
    def test_cached_api_post_reaches_protected_reader_with_its_original_body(
        self, reader
    ):
        reader.return_value = (
            {'description': 'Fictional offer'},
            'https://example.invalid/job',
        )
        self.client.force_login(self.employer)
        response = self.client.post(
            '/api/imports/source/',
            {'agreement': 'true', 'kind': 'url', 'url': 'https://example.invalid/job'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [('/api/job-offers/source/', 308)])
        self.assertEqual(response.json()['data']['description'], 'Fictional offer')
        reader.assert_called_once_with('https://example.invalid/job')
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post('/api/imports/source/', {})
            .status_code,
            403,
        )

    def test_return_url_is_fixed_local_and_keeps_only_one_valid_language(self):
        from eures_beta.www.accounts.return_path import canonical_destination

        for destination in (
            'https://attacker.invalid/employer/import/',
            '//attacker.invalid/employer/import/',
            '/admin/',
            '/employer/import/?next=https://attacker.invalid',
            '/employer/import/?lang=fr&lang=de',
            '/employer/import/?lang=unknown',
            '/employer/import/#external',
        ):
            self.assertEqual(canonical_destination(destination), '', destination)
        for language in ('fr', 'en', 'de'):
            self.assertEqual(
                canonical_destination('/employer/pages/import-' + language + '.html'),
                '/employer/import/?lang=' + language,
            )
