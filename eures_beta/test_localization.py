from django.urls import reverse


from eures_beta.testing_support import DomainScenario


class LocalizationTests(DomainScenario):
    def test_three_languages_and_no_private_cache(self):
        self.as_role('adviser')
        for lang, expected in [
            ('fr', 'Mon espace'),
            ('en', 'My workspace'),
            ('de', 'Mein Bereich'),
        ]:
            self.client.cookies['django_language'] = lang
            response = self.client.get(reverse('dashboard'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response.headers['Cache-Control'])
            self.assertContains(response, expected)
            self.assertContains(response, f'<html lang="{lang}">')
