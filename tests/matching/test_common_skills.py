from datetime import date
from django.test import SimpleTestCase
from eures_beta.matching.engine import evaluate
from eures_beta.occupations import unified
from eures_beta.skills import common_source


class CommonSkillMatchingTests(SimpleTestCase):
    def skill_rows(self, candidate, offer):
        result = evaluate(candidate, offer, today=date(2026, 11, 19))
        return [row for row in result['rows'] if row['dimension'] == 'skills']

    def test_same_explicit_rome_skill_matches_without_an_esco_bridge(self):
        ref = 'rome:D1108'
        source = common_source.source_for(ref)
        key = next(
            key
            for key, row in source['skills'].items()
            if row['kind'] == 'skill' and row['scheme'] == 'ROME'
        )
        selections = {source['key']: {'skills': [key]}}
        rows = self.skill_rows(
            {'occupation_skills': selections}, {'occupationSkills': selections}
        )
        self.assertEqual(rows[0]['state'], 'match')
        self.assertTrue(common_source.skill_label(key, 'fr'))

    def test_occupation_equivalence_or_matching_wording_never_proves_skill_equivalence(
        self,
    ):
        candidate = {
            'occupation_skills': {
                'rome:D1102': {
                    'skills': ['rome:competence:123'],
                    'sources': {'alias': 'same wording'},
                }
            }
        }
        offer = {
            'occupationSkills': {
                'http://data.europa.eu/esco/occupation/1aadb308-432a-4d01-b54b-b4f7f76dd419': {
                    'skills': ['http://data.europa.eu/esco/skill/other']
                }
            }
        }
        rows = self.skill_rows(candidate, offer)
        self.assertEqual(rows[0]['state'], 'unknown')
        self.assertEqual(rows[0]['reason'], 'not_declared')

    def test_two_official_aliases_are_one_occupation_but_not_two_alternative_requirements(
        self,
    ):
        code = next(iter(unified.pairs()))
        uri = unified.pairs()[code]['uri']
        offer = {
            'occupationSkills': {
                uri: {'skills': ['same']},
                'rome:' + code: {'skills': ['same']},
            }
        }
        rows = self.skill_rows({'acquired_skills': ['same']}, offer)
        self.assertEqual(rows[0]['state'], 'match')
