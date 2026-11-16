"""Reference grammar, API bounds and non-backtracking queries (CodeQL 3/13–15)."""

import subprocess
import sys
from unittest.mock import patch

from django.test import SimpleTestCase

from eures_beta.occupations.catalog import (
    is_rome_reference,
    looks_like_reference,
    search_title,
    strip_reference_prefix,
)


class ReferenceQueryTests(SimpleTestCase):
    def test_known_prefixes_delimiters_and_unicode_whitespace(self):
        for query in ('ROME A1234', 'rome: A1234', 'ROME\u2003—\tA1234', 'ROME-A1234'):
            self.assertTrue(is_rome_reference(query))
            self.assertEqual(strip_reference_prefix(query), 'A1234')
        self.assertTrue(is_rome_reference('a1234'))
        self.assertEqual(strip_reference_prefix('ESCO: 1.2.3'), '1.2.3')
        self.assertEqual(strip_reference_prefix('ESCO: 1.2', ('ROME',)), 'ESCO: 1.2')

    def test_reference_classification_preserves_existing_forms(self):
        for query in (
            'ROME: A1234',
            'A1234',
            'ESCO 1.2',
            'ESCO: ',
            'ESCO\n: 1.2',
            '1.2.3',
            '١.٢',
            '12345678-1234-1234-1234-123456789abc',
            'https://data.europa.eu/esco/occupation/12345678-1234-1234-1234-123456789abc',
        ):
            with self.subTest(query=query):
                self.assertTrue(looks_like_reference(query))
        for query in (
            '',
            'ROME',
            'ROME : ',
            'ESCO',
            'ESCO foo\nbar',
            '1..2',
            '1.',
            'boulanger',
        ):
            with self.subTest(query=query):
                self.assertFalse(looks_like_reference(query))

    def test_rome_codes_are_exact_and_do_not_accept_esco_prefix(self):
        for query in (
            'A123',
            'AA1234',
            'A12345',
            'ROME::A1234',
            'ESCO A1234',
            'ROME A1234!',
        ):
            self.assertFalse(is_rome_reference(query))

    def test_annotations_keep_qualifications_but_remove_contract_suffix(self):
        for title, expected in (
            ('Boulanger   —   CDI', 'boulanger'),
            ('Bäcker (m/w/d) , part-time', 'backer'),
            ('Cook | 35 h', 'cook'),
            ('Boulanger - pâtissier', 'boulanger patissier'),
            ('Chef (débutant) – missions variées', 'chef debutant missions variees'),
        ):
            self.assertEqual(search_title(title), expected)

    def test_repeated_whitespace_is_safe_even_outside_the_api_bound(self):
        script = '''
from eures_beta.occupations.catalog import search_title, is_rome_reference, looks_like_reference
assert search_title('Boulanger' + ' ' * 100000 + '!') == 'boulanger'
assert search_title('Boulanger' + ' ' * 100000 + '— CDI') == 'boulanger'
assert not is_rome_reference('ROME' + ' ' * 100000 + '!')
assert not looks_like_reference('ROME' + ' ' * 100000 + '!')
'''
        result = subprocess.run(
            [sys.executable, '-c', script], capture_output=True, text=True, timeout=5
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @patch('eures_beta.www.occupations.views.occupation_index')
    def test_api_rejects_oversized_query_before_catalog_or_reference_work(self, index):
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    '/api/occupations/',
                    {'q': 'x' * 151},
                    **(
                        {'content_type': 'application/json'} if method == 'post' else {}
                    ),
                )
                self.assertEqual(response.status_code, 400)
        index.assert_not_called()

    @patch(
        'eures_beta.www.occupations.views.catalog',
        return_value={'manifest': {'version': 'test'}},
    )
    @patch(
        'eures_beta.www.occupations.views.rome_suggestions',
        return_value=[{'code': 'A1234'}],
    )
    @patch(
        'eures_beta.www.occupations.views.references',
        return_value=[{'uri': 'fictional'}],
    )
    def test_independent_rome_code_never_becomes_an_esco_match(
        self, references, rome, catalog
    ):
        response = self.client.post(
            '/api/occupations/',
            {'q': 'ROME: A1234', 'independent': True},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])
        self.assertEqual(response.json()['rome_results'], [{'code': 'A1234'}])
        references.assert_not_called()
        rome.assert_called_once()
