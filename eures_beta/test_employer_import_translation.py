import json
import re

from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True, DEMO_MODE=True)
class EmployerImportTranslationTests(SimpleTestCase):
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
                    f'/employer/pages/import-{language}.html', secure=True
                )
                self.assertTemplateUsed(response, 'employer/import.html')
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, f'href="privacy-{language}.html"')
                self.assertContains(
                    response,
                    f'class="lang-link is-active" href="import-{language}.html"',
                )
                html = response.content.decode()
                scripts = dict(
                    re.findall(
                        r'<script id="([^"]+)" type="application/json">(.*?)</script>',
                        html,
                        re.S,
                    )
                )
                strings = json.loads(scripts['import-strings'])
                self.assertEqual(strings['continue'], label)
                self.assertTrue(strings['errors'])
                self.assertTrue(json.loads(scripts['contact-strings'])['privacy'])
                self.assertNotIn('{%', html)
