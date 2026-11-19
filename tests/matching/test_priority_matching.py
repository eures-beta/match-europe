from datetime import date

from django.test import SimpleTestCase
from django.utils import translation

from eures_beta.matching.engine import evaluate, WEIGHTS
from eures_beta.matching.presentation import present
from eures_beta.occupations import unified


class PriorityMatchingTests(SimpleTestCase):
    def evaluate(self, candidate, offer):
        return evaluate(candidate, offer, today=date(2026, 11, 19))

    def occupation(self, result):
        return next(row for row in result['rows'] if row['key'] == 'occupation')

    def test_official_alias_confirms_interest_but_never_proves_skills(self):
        code, pair = next(iter(unified.pairs().items()))
        result = self.evaluate(
            {'occupation_references': ['rome:' + code]},
            {'occupation': {'uris': [pair['uri']]}},
        )
        self.assertEqual(self.occupation(result)['state'], 'match')
        self.assertEqual(result['established'], 10)
        skills = next(d for d in result['dimensions'] if d['key'] == 'skills')
        self.assertEqual(skills['established'], 0)
        self.assertEqual(skills['unresolved'], 40)

    def test_shared_skills_outweigh_matching_occupation(self):
        code = next(iter(unified.pairs()))
        offer = {
            'occupation': {'rome_codes': [code]},
            'occupationSkills': {'rome:' + code: {'skills': ['a', 'b']}},
        }
        interest = self.evaluate({'occupation_references': ['rome:' + code]}, offer)
        transferable = self.evaluate({'acquired_skills': ['a', 'b']}, offer)
        self.assertEqual(interest['established'], 10)
        self.assertEqual(transferable['established'], 40)
        self.assertGreater(transferable['established'], interest['established'])
        self.assertEqual(sum(WEIGHTS.values()), 100)

    def test_open_project_never_infers_interest_from_old_references(self):
        result = self.evaluate(
            {'project_mode': 'open', 'occupation_references': ['rome:D1102']},
            {'occupation': {'rome_codes': ['D1102']}},
        )
        self.assertEqual(self.occupation(result)['state'], 'unknown')
        self.assertFalse(result['blocked'])

    def test_other_job_unknown_reference_and_free_title_never_prove_interest(self):
        for candidate in (
            {'occupation_references': ['rome:D1108']},
            {'occupation_references': ['unknown']},
            {'desired_occupations': 'Boulanger'},
            {'occupation_skills': {'rome:D1102': {'skills': []}}},
        ):
            with self.subTest(candidate=candidate):
                result = self.evaluate(
                    candidate, {'occupation': {'rome_codes': ['D1102']}}
                )
                self.assertEqual(self.occupation(result)['state'], 'unknown')
                self.assertEqual(result['established'], 0)
                self.assertFalse(result['blocked'])

    def test_duplicate_aliases_never_multiply_occupation_points(self):
        code, pair = next(iter(unified.pairs().items()))
        result = self.evaluate(
            {'occupation_references': ['rome:' + code, 'esco:' + pair['uri']]},
            {'occupation': {'uris': [pair['uri']], 'rome_codes': [code]}},
        )
        self.assertEqual(result['established'], 10)
        self.assertEqual(
            len([r for r in result['rows'] if r['key'] == 'occupation']), 1
        )

    def test_only_shared_priorities_across_alternative_jobs_can_earn_points(self):
        result = self.evaluate(
            {'acquired_skills': ['shared', 'a', 'b']},
            {
                'occupationSkills': {
                    'one': {'skills': ['shared', 'a']},
                    'two': {'skills': ['shared', 'b']},
                }
            },
        )
        rows = {r['reference']: r for r in result['rows'] if r['key'] == 'skill'}
        self.assertEqual(rows['shared']['state'], 'match')
        for ref in ('a', 'b'):
            self.assertEqual(rows[ref]['state'], 'unknown')
            self.assertEqual(rows[ref]['reason'], 'alternative_occupations')

    def test_unchecked_priority_remains_unknown_even_in_matching_job(self):
        result = self.evaluate(
            {'occupation_references': ['rome:D1102']},
            {
                'occupation': {'rome_codes': ['D1102']},
                'occupationSkills': {'rome:D1102': {'skills': ['unchecked']}},
            },
        )
        row = next(r for r in result['rows'] if r['key'] == 'skill')
        self.assertEqual((row['state'], row['reason']), ('unknown', 'not_declared'))
        self.assertFalse(result['blocked'])

    def test_occupation_presentation_in_three_languages(self):
        result = self.evaluate(
            {'occupation_references': ['rome:D1102']},
            {'occupation': {'rome_codes': ['D1102']}},
        )
        for language in ('fr', 'en', 'de'):
            with self.subTest(language=language), translation.override(language):
                row = self.occupation(present(result, language))
                self.assertTrue(row['reference_label'])
                self.assertNotIn('rome:', row['reference_label'])
                self.assertTrue(str(row['explanation']))
