import json
import re

from django.test import SimpleTestCase, override_settings
from eures_beta.occupations.catalog import suggestions


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class OccupationSearchTests(SimpleTestCase):
    def test_search_api_uses_local_catalog_and_enforces_access_and_limits(self):
        for lang, query in [('fr', 'boulanger'), ('en', 'baker'), ('de', 'Bäcker')]:
            response = self.client.get(
                '/api/occupations/', {'q': query, 'lang': lang}, secure=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json()['results'][0]['uri'],
                suggestions('boulanger', 'fr')[0]['uri'],
            )
        for params in (
            {'q': 'x' * 151},
            {'q': 'boulanger', 'lang': 'xx'},
            {'q': 'boulanger', 'excluded': ['invalid']},
        ):
            self.assertEqual(
                self.client.get('/api/occupations/', params, secure=True).status_code,
                400,
            )
        self.assertEqual(
            self.client.get('/api/occupations/', {'q': 'boulanger'}).status_code, 404
        )
        self.assertEqual(
            self.client.post('/api/occupations/', secure=True).status_code, 405
        )
        with override_settings(DEMO_MODE=False):
            self.assertEqual(
                self.client.get(
                    '/api/occupations/', {'q': 'boulanger'}, secure=True
                ).status_code,
                404,
            )

    def test_employer_page_translates_picker_and_renders_safe_json(self):
        for lang, expected in [
            ('fr', 'Précisez le métier proposé'),
            ('en', 'Describe the job offered'),
            ('de', 'Beschreiben Sie den angebotenen Beruf'),
        ]:
            response = self.client.get(
                f'/employer/pages/import-{lang}.html', secure=True
            )
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            match = re.search(
                r'<script id="occupation-strings" type="application/json">(.*?)</script>',
                html,
                re.S,
            )
            strings = json.loads(match.group(1))
            self.assertEqual(strings['heading'], expected)
            self.assertTrue(strings['required'])
            self.assertEqual(html.count('occupation-picker.js'), 1)
            self.assertEqual(html.count('id="review-form"'), 1)
