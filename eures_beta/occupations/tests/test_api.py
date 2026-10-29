import json
import re

from django.test import SimpleTestCase, Client, override_settings
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
            self.client.put('/api/occupations/', secure=True).status_code, 405
        )
        with override_settings(DEMO_MODE=False):
            self.assertEqual(
                self.client.get(
                    '/api/occupations/', {'q': 'boulanger'}, secure=True
                ).status_code,
                404,
            )

    def test_annotated_generic_title_uses_explicit_multilingual_offer_context(self):
        payload = {
            'q': 'Agent de service (m/f/x) - CDI, 40h/semaine',
            'lang': 'fr',
            'context': 'Full-time. Quick service restaurant crew member.',
        }
        response = self.client.post(
            '/api/occupations/',
            json.dumps(payload),
            content_type='application/json',
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['results'][0]['label'],
            'équipier polyvalent de restauration rapide/équipière polyvalente de restauration rapide',
        )
        self.assertEqual(payload['q'], 'Agent de service (m/f/x) - CDI, 40h/semaine')
        self.assertEqual(
            suggestions('boulanger (H/F) - CDI, 35h/semaine', 'fr')[0]['uri'],
            suggestions('boulanger', 'fr')[0]['uri'],
        )
        self.assertEqual(
            suggestions('boulanger', 'fr', payload['context'])[0]['uri'],
            suggestions('boulanger', 'fr')[0]['uri'],
        )
        for changes in ({'context': 'x' * 20001}, {'excluded': [{}]}, {'q': []}):
            self.assertEqual(
                self.client.post(
                    '/api/occupations/',
                    json.dumps({**payload, **changes}),
                    content_type='application/json',
                    secure=True,
                ).status_code,
                400,
            )
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(
                '/api/occupations/',
                json.dumps(payload),
                content_type='application/json',
                secure=True,
            )
            .status_code,
            403,
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
