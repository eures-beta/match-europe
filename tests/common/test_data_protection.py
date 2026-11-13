from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class DataProtectionTests(SimpleTestCase):
    def test_notice_is_public_translated_and_states_the_inherited_periods(self):
        for language, title, period, limit in (
            (
                'fr',
                'Protection et conservation des données',
                '12 mois après le dernier contact utile.',
                'effacement automatique n’est pas encore mise en œuvre',
            ),
            (
                'en',
                'Data protection and retention',
                '12 months after the last useful contact.',
                'Automatic deletion according to these periods is not yet implemented',
            ),
            (
                'de',
                'Datenschutz und Aufbewahrung',
                '12 Monate nach dem letzten zweckdienlichen Kontakt.',
                'automatische Löschung nach diesen Fristen ist in dieser Version noch nicht umgesetzt',
            ),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'en' if language == 'fr' else 'fr'
                )
                response = self.client.get(reverse('privacy'), {'lang': language})
                self.assertContains(response, title)
                self.assertContains(response, period)
                self.assertContains(response, limit)
                self.assertContains(
                    response,
                    {
                        'fr': 'Vos droits et contact',
                        'en': 'Your rights and contact',
                        'de': 'Ihre Rechte und Kontakt',
                    }[language],
                )
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, '<th scope="row">', count=6)
                self.assertContains(response, '24 ')
                self.assertContains(response, '6 ')
                self.assertContains(
                    response,
                    {'fr': '2 heures', 'en': '2 hours', 'de': '2 Stunden'}[language],
                )
                self.assertContains(response, 'mailto:eric.barthelemy@francetravail.fr')
                self.assertNotContains(response, f'/employer/privacy/?lang={language}')
                for target in ('fr', 'en', 'de'):
                    self.assertContains(response, f'href="/privacy/?lang={target}"')
                self.assertNotContains(response, '<form')

    def test_notice_rejects_writes_and_does_not_create_a_session(self):
        url = reverse('privacy')
        self.assertEqual(self.client.head(url).status_code, 200)
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(url).status_code, 405)
        self.assertNotIn('sessionid', self.client.cookies)

    def test_unknown_language_falls_back_to_french_and_home_links_to_notice(self):
        response = self.client.get(reverse('privacy'), {'lang': 'invalid'})
        self.assertContains(response, '<html lang="fr">')
        for language in ('fr', 'en', 'de'):
            self.assertContains(
                self.client.get(reverse('home'), {'lang': language}),
                f'href="/privacy/?lang={language}"',
            )

    def test_notice_describes_verified_registration_and_two_hour_drafts(self):
        response = self.client.get(reverse('privacy'), {'lang': 'en'})
        self.assertContains(
            response,
            'Your answers await email confirmation for one hour.',
        )
        self.assertContains(response, 'expires after 2 hours without activity.')
        self.assertContains(
            response, 'Confirmation creates a candidate account and saves the profile.'
        )
        self.assertNotContains(
            response, 'Your email is verified before the questionnaire.'
        )
