from eures_beta.testing import assert_active_link, json_scripts
import json

from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True, DEMO_MODE=True)
class EmployerImportTranslationTests(SimpleTestCase):
    page = "import"

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
                self.assertTemplateUsed(response, f'employer/{self.page}.html')
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, f'href="privacy-{language}.html"')
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


class EmployerImportV2TranslationTests(EmployerImportTranslationTests):
    page = "import-v2"
