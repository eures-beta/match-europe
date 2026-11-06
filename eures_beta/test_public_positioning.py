from django.test import SimpleTestCase, override_settings


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class PublicPositioningTests(SimpleTestCase):
    def test_matching_limits_and_consent_are_visible_in_all_three_languages(self):
        for language, signature, unavailable, adviser_promise in (
            (
                'fr',
                'Des mises en relation consenties.',
                'ne sont pas encore disponibles.',
                'avec l’appui',
            ),
            (
                'en',
                'Introductions by mutual consent.',
                'not yet available.',
                'with support from',
            ),
            (
                'de',
                'Kontaktaufnahme im beiderseitigen Einvernehmen.',
                'noch nicht verfügbar.',
                'mit Unterstützung',
            ),
        ):
            for path in ('/', '/candidate/', f'/employer/pages/{language}.html'):
                with self.subTest(language=language, path=path):
                    response = self.client.get(path, {'lang': language}, secure=True)
                    self.assertContains(response, signature)
                    self.assertContains(response, unavailable)
                    self.assertContains(response, '<h1>', count=1)
                    self.assertContains(response, 'id="main-content"', count=1)
                    self.assertContains(response, 'href="#main-content"')
                    self.assertNotContains(response, adviser_promise)

    def test_home_puts_both_journeys_before_project_context(self):
        body = self.client.get('/?lang=en', secure=True).content.decode()
        self.assertLess(
            body.index('Work in another country'), body.index('home-stats-title')
        )
        self.assertLess(
            body.index('Recruit in another country'), body.index('home-stats-title')
        )
