from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True)
class EmployerLandingTranslationTests(SimpleTestCase):
    def test_one_template_translates_content_navigation_and_accessibility_labels(self):
        examples = [
            ('fr', 'Recrutez', 'Aller au contenu'),
            ('en', 'Make recruitment easier', 'Skip to content'),
            ('de', 'Einfacher Personal finden', 'Zum Inhalt'),
        ]
        for language, heading, skip in examples:
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'en' if language != 'en' else 'fr'
                )
                response = self.client.get(
                    f'/employer/pages/{language}.html', secure=True
                )
                self.assertTemplateUsed(response, 'employer/landing.html')
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, heading)
                self.assertContains(response, skip)
                self.assertContains(response, f'href="import-v2-{language}.html"')
                self.assertContains(response, f'href="privacy-{language}.html"')
                self.assertContains(
                    response, f'href="/employer/access/?lang={language}"'
                )
                self.assertContains(
                    response, f'class="lang-link is-active" href="{language}.html"'
                )
