from eures_beta.testing import assert_active_link
from django.test import SimpleTestCase, override_settings
from django.templatetags.static import static
from django.contrib.staticfiles import finders


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class CandidateLandingTests(SimpleTestCase):
    def test_candidate_routes_belong_to_the_candidate_application(self):
        from django.urls import resolve

        for path in ('/candidate/', '/forms/eures-beta/candidate'):
            self.assertEqual(
                resolve(path).func.__module__, 'eures_beta.candidates.landing'
            )

    def test_languages_choices_and_separation_from_employer(self):
        for language, title in (
            ('fr', 'Trouvez votre prochain emploi en Europe'),
            ('en', 'Find your next job in Europe'),
            ('de', 'Finden Sie Ihren nächsten Job in Europa'),
        ):
            with self.subTest(language=language):
                response = self.client.get(
                    '/candidate/', {'lang': language}, secure=True
                )
                self.assertTemplateUsed(response, 'candidates/landing.html')
                self.assertContains(response, title)
                body = response.content.decode()
                self.assertEqual(body.count('data-candidate-choice='), 3)
                self.assertIn('data-candidate-account', body)
                for forbidden in (
                    'data-employer-account',
                    'data-employer-api',
                    '<form',
                    'type="file"',
                ):
                    self.assertNotIn(forbidden, body)
                for target in ('fr', 'en', 'de'):
                    self.assertIn(f'href="/candidate/?lang={target}"', body)
                for asset in ('candidate.css', 'candidate.js'):
                    self.assertIn(static(f'candidate/{asset}'), body)
                    self.assertTrue(finders.find(f'candidate/{asset}'))
                self.assertNotIn('src="assets/', body)

    def test_shell_and_browser_notices_use_the_selected_language(self):
        for language, skip, navigation, notice in (
            (
                'fr',
                'Aller au contenu',
                'Navigation principale',
                'La connexion candidat sera préparée dans une prochaine étape.',
            ),
            (
                'en',
                'Skip to content',
                'Main navigation',
                'Candidate sign-in will be prepared in a later step.',
            ),
            (
                'de',
                'Zum Inhalt',
                'Hauptnavigation',
                'Die Anmeldung für Bewerbende folgt in einem späteren Schritt.',
            ),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'fr' if language == 'en' else 'en'
                )
                response = self.client.get(
                    '/candidate/', {'lang': language}, secure=True
                )
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, skip)
                self.assertContains(response, f'aria-label="{navigation}"')
                self.assertContains(response, notice)
                self.assertContains(response, f'href="/employer/pages/{language}.html"')
                assert_active_link(self, response, f'/candidate/?lang={language}')

    def test_legacy_entry_and_unsupported_language(self):
        for path in ('/candidate/', '/forms/eures-beta/candidate'):
            self.assertContains(
                self.client.get(path, {'lang': 'en'}, secure=True),
                'Find your next job in Europe',
            )
            self.assertContains(
                self.client.get(path, {'lang': '../../invalid'}, secure=True),
                '<html lang="fr">',
            )

    def test_rejects_writes_and_is_closed_outside_demo(self):
        for path in ('/candidate/', '/forms/eures-beta/candidate'):
            self.assertEqual(self.client.post(path, secure=True).status_code, 405)
            self.assertEqual(self.client.get(path).status_code, 404)
            with override_settings(DEMO_MODE=False):
                self.assertEqual(self.client.get(path, secure=True).status_code, 404)

    @override_settings(SHARED_DEMO=False)
    def test_local_access_does_not_allow_remote_clients(self):
        from unittest.mock import patch

        with patch.dict('os.environ', {'ME_EMPLOYER_DEV_ACCESS': '1'}):
            self.assertEqual(
                self.client.get('/candidate/', REMOTE_ADDR='127.0.0.1').status_code, 200
            )
            self.assertEqual(
                self.client.get('/candidate/', REMOTE_ADDR='192.0.2.42').status_code,
                404,
            )
