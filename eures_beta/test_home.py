from django.test import SimpleTestCase, override_settings


class PublicHomeTests(SimpleTestCase):
    def test_reference_content_and_journey_links_in_each_language(self):
        for demo_mode in (False, True):
            for path in ('/', '/forms/eures-beta/'):
                for language, title, figures, outlook in (
                    (
                        'fr',
                        'Faciliter les recrutements',
                        'Quelques repères',
                        'Perspectives',
                    ),
                    ('en', 'Facilitating recruitment', 'A few figures', 'Outlook'),
                    (
                        'de',
                        'Personalgewinnung und berufliche Mobilität',
                        'Einige Kennzahlen',
                        'Ausblick',
                    ),
                ):
                    with (
                        self.subTest(demo=demo_mode, path=path, language=language),
                        override_settings(DEMO_MODE=demo_mode),
                    ):
                        self.client.cookies['django_language'] = (
                            'de' if language == 'fr' else 'fr'
                        )
                        response = self.client.get(path, {'lang': language})
                        self.assertContains(response, f'<html lang="{language}">')
                        for text in (
                            title,
                            figures,
                            outlook,
                            'home-stats-title',
                            'aria-current="page"',
                        ):
                            self.assertContains(response, text)
                        for target in ('fr', 'en', 'de'):
                            self.assertContains(response, f'href="/?lang={target}"')
                        self.assertContains(
                            response, f'href="/candidate/?lang={language}"'
                        )
                        self.assertContains(
                            response, f'href="/employer/pages/{language}.html"'
                        )
                        self.assertNotContains(response, '<form')
                        self.assertNotContains(response, 'data-employer-api')

    def test_invalid_language_and_writes(self):
        self.assertContains(self.client.get('/?lang=invalid'), '<html lang="fr">')
        for path in ('/', '/forms/eures-beta/'):
            self.assertEqual(self.client.post(path).status_code, 405)

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_home_navigation_from_both_journeys(self):
        for language in ('fr', 'en', 'de'):
            for path in (
                f'/candidate/?lang={language}',
                f'/employer/pages/{language}.html',
            ):
                response = self.client.get(path, secure=True)
                target = f'/forms/eures-beta/?lang={language}'
                self.assertContains(response, f'href="{target}"')
                home = self.client.get(target, secure=True)
                self.assertTemplateUsed(home, 'home.html')
                self.assertContains(home, f'<html lang="{language}">')
