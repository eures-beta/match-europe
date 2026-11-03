"""Guard the real search pipeline against malformed-title CPU exhaustion."""

import json
import subprocess
import sys
from django.test import SimpleTestCase


class SearchPerformanceTests(SimpleTestCase):
    def test_recruitment_annotations_keep_the_existing_normalization(self):
        from eures_beta.occupations.catalog import search_title

        for title, expected in (
            ('Boulanger (H/F)', 'boulanger'),
            ('Bäcker (m/w/d) – CDI', 'backer'),
            ('Cook (f/m/x)', 'cook'),
            ('Chef (h) cuisine', 'chef h cuisine'),
            ('Poste (/hf)', 'poste hf'),
            ('Poste ( / )', 'poste'),
            ('Boulanger (débutant)', 'boulanger debutant'),
        ):
            with self.subTest(title=title):
                self.assertEqual(search_title(title), expected)

    def test_malformed_annotations_finish_without_blocking_the_test_runner(self):
        # Run in a separate process: a catastrophic regex holds the GIL, so a
        # thread timeout would not protect the test runner itself.
        titles = [
            'Poste (' + 'h' * 32,
            'Poste (' + 'h' * 32 + 'a)',
            'Poste (' + ' ' * 100 + 'a)',
        ]
        program = '''
import json, sys
from eures_beta.occupations.catalog import search_title, suggestions, rome_suggestions
titles = json.loads(sys.argv[1])
for title in titles:
    normalized = search_title(title)
    assert normalized.startswith('poste ')
    assert 'h' * 32 in normalized or 'a' in normalized
    for language in ('fr', 'en', 'de'):
        suggestions(title, language)
    rome_suggestions(title)
'''
        try:
            result = subprocess.run(
                [sys.executable, '-c', program, json.dumps(titles)],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            self.fail(
                'Malformed-title searches exceeded five seconds in an isolated process'
            )
        self.assertEqual(result.returncode, 0, result.stderr)
