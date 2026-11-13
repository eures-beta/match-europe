from tests.helpers import assert_active_link, json_scripts
import json

from django.test import TestCase, override_settings


class JobOfferTranslationTests(TestCase):
    page = "import"

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(
            get_user_model().objects.create_user(
                email="translation@example.invalid", kind="employer"
            )
        )

    def test_import_form_and_browser_dictionaries_follow_the_url_language(self):
        for language, label in (
            ('en', 'Continue'),
            ('fr', 'Continuer'),
            ('de', 'Weiter'),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'fr' if language == 'en' else 'en'
                )
                response = self.client.get(
                    f'/employer/pages/{self.page}-{language}.html', secure=True
                )
                self.assertContains(response, 'id="development-notice"', count=1)
                self.assertContains(response, 'mailto:eric.barthelemy@francetravail.fr')
                self.assertNotContains(response, 'Démonstration partagée')
                self.assertNotContains(response, 'Shared demonstration:')
                self.assertNotContains(response, 'Geteilte Demonstration')
                self.assertTemplateUsed(response, f'employer/{self.page}.html')
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, f'href="/privacy/?lang={language}"')
                assert_active_link(self, response, f'{self.page}-{language}.html')
                html = response.content.decode()
                scripts = json_scripts(response)
                strings = json.loads(scripts['import-strings'])
                self.assertEqual(strings['continue'], label)
                self.assertTrue(strings['errors'])
                self.assertTrue(strings['errors']['session_expired'])
                self.assertTrue(strings['connectedContactTitle'])
                self.assertTrue(strings['connectedContactHelp'])
                review = json.loads(scripts['review-strings'])
                self.assertTrue(review['errors']['search_started'])
                self.assertTrue(json.loads(scripts['contact-strings'])['privacy'])
                self.assertNotIn('{%', html)


class JobOfferCompatibilityTests(TestCase):
    def test_abandoned_variant_redirects_to_the_single_journey_in_all_languages(self):
        from django.contrib.auth import get_user_model

        employer = get_user_model().objects.create_user(
            email='canonical-import@example.invalid', kind='employer'
        )
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(employer)
            for language in ('fr', 'en', 'de'):
                with self.subTest(authenticated=authenticated, language=language):
                    old = f'/employer/pages/import-v2-{language}.html'
                    canonical = f'/employer/pages/import-{language}.html'
                    response = self.client.get(old + '?example=one%20two', secure=True)
                    self.assertRedirects(
                        response,
                        canonical + '?example=one%20two',
                        status_code=301,
                        fetch_redirect_response=False,
                    )
                    page = self.client.get(canonical, secure=True)
                    self.assertTemplateUsed(
                        page,
                        (
                            'employer/import.html'
                            if authenticated
                            else 'employer/import_access.html'
                        ),
                    )
                    self.assertNotContains(page, 'href="import-v2-')
        self.assertEqual(
            self.client.get('/employer/pages/import-v2.html').status_code, 404
        )

    def test_old_login_destinations_are_normalized_without_allowing_external_urls(self):
        from django.test import RequestFactory
        from eures_beta.www.accounts.return_path import consume, remember

        for language in ('fr', 'en', 'de'):
            old = f'/employer/pages/import-v2-{language}.html'
            canonical = f'/employer/pages/import-{language}.html'
            request = RequestFactory().get('/accounts/login/', {'next': old})
            request.session = {}
            remember(request)
            self.assertEqual(request.session['login_return_path'], canonical)
            request.session['login_return_path'] = old
            self.assertEqual(consume(request, '/accounts/dashboard/'), canonical)
        request.session['login_return_path'] = 'https://attacker.invalid/'
        self.assertEqual(
            consume(request, '/accounts/dashboard/'), '/accounts/dashboard/'
        )
