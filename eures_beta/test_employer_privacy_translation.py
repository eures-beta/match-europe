from eures_beta.testing import assert_active_link
from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True, DEMO_MODE=True)
class EmployerPrivacyTranslationTests(SimpleTestCase):
    def test_notice_and_navigation_follow_the_url_language(self):
        for language, title in (
            ('en', 'How Match Europe uses your information'),
            ('fr', 'Comment Match Europe utilise vos informations'),
            ('de', 'Wie Match Europe Ihre Angaben verwendet'),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'fr' if language == 'en' else 'en'
                )
                response = self.client.get(
                    f'/employer/pages/privacy-{language}.html', secure=True
                )
                self.assertContains(response, 'id="development-notice"', count=1)
                self.assertContains(response, 'mailto:eric.barthelemy@francetravail.fr')
                self.assertNotContains(response, 'Démonstration partagée')
                self.assertNotContains(response, 'Shared demonstration:')
                self.assertNotContains(response, 'Geteilte Demonstration')
                self.assertTemplateUsed(response, 'employer/privacy.html')
                self.assertContains(response, title)
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, f'href="{language}.html"')
                assert_active_link(self, response, f'privacy-{language}.html')
