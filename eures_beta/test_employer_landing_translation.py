from eures_beta.testing import assert_active_link
from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True)
class EmployerLandingTranslationTests(SimpleTestCase):
    def test_one_template_translates_content_navigation_and_accessibility_labels(self):
        examples = [
            (
                'fr',
                'Recrutez',
                'Aller au contenu',
                'Vos offres sont enregistrées.',
                'Aucun rapprochement n’est effectué à ce stade.',
            ),
            (
                'en',
                'Make recruitment easier',
                'Skip to content',
                'Your offers are saved.',
                'No matching is carried out at this stage.',
            ),
            (
                'de',
                'Einfacher Personal finden',
                'Zum Inhalt',
                'Ihre Angebote werden gespeichert.',
                'Derzeit findet noch kein Abgleich statt.',
            ),
        ]
        for language, heading, skip, saved, pending in examples:
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
                self.assertContains(response, f'href="import-{language}.html"')
                import_response = self.client.get(
                    f'/employer/pages/import-{language}.html', secure=True
                )
                self.assertContains(
                    import_response, '/static/employer/occupation-picker.js'
                )
                self.assertContains(import_response, '/static/employer/review-steps.js')
                self.assertContains(response, f'href="privacy-{language}.html"')
                self.assertContains(
                    response, f'href="/employer/access/?lang={language}"'
                )
                assert_active_link(self, response, f'{language}.html')
                self.assertContains(response, saved)
                self.assertContains(response, pending)
                self.assertContains(
                    response, 'href="mailto:eric.barthelemy@francetravail.fr"'
                )
                self.assertContains(
                    response, '/static/employer/assets/match-europe-logo.png'
                )
                self.assertContains(response, 'id="development-notice"', count=1)
                self.assertNotContains(response, 'External saving and Push diagnostics')
                self.assertNotContains(response, 'Démonstration partagée')
                self.assertNotContains(response, 'Geteilte Demonstration')
