import json
from copy import deepcopy
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from eures_beta.occupations import unified
from eures_beta.occupations.catalog import (
    occupation_index,
    rome_search_catalog,
    normalize,
)
from eures_beta.skills import (
    common_source,
    common_suggestions,
    albert_skills,
    continuous,
)
from eures_beta.skills.models import OccupationSkillSuggestion
from eures_beta.skills.skills_pilot import catalogue
from eures_beta.candidates.forms import ProjectForm, KEY
from tests.candidates.test_registration import answers
from eures_beta.employers.occupation_selection import clean_selection
from eures_beta.employers.offer_ingestion import empty_data
from eures_beta.www.employer.imports import clean_data
from eures_beta.users.models import User


@override_settings(CONTINUOUS_SKILLS_ENABLED=True, EMAIL_DELIVERY_ENABLED=False)
class CommonCatalogueTests(TestCase):
    def setUp(self):
        cards, _ = catalogue()
        covered = {row['occupation']['uri'] for row in cards.values()}
        self.uri = next(uri for uri in occupation_index() if uri not in covered)
        self.source = common_source.source_for(self.uri)
        self.keys = common_source.balanced(self.source, 8)

    def test_full_portable_sources_cover_both_catalogues_and_have_verified_identity(
        self,
    ):
        files = common_source.manifest()['files']
        self.assertTrue(
            all(
                'esco/' + uri.rsplit('/', 1)[1] + '.json' in files
                for uri in occupation_index()
            )
        )
        self.assertTrue(
            all(
                'rome/' + code + '.json' in files
                for code in rome_search_catalog()['fiches']
            )
        )
        self.assertEqual(
            len(files),
            len(occupation_index()) + len(rome_search_catalog()['fiches']) + 1,
        )
        self.assertEqual(common_source.source_slice(self.uri)['reference'], self.uri)
        self.assertEqual(
            common_source.skill_label(
                'http://data.europa.eu/esco/skill/d87653a0-87b0-4c03-a44a-bf0a217431a2',
                'fr',
            ),
            'pétrir des denrées alimentaires',
        )
        for code in ('D1108', 'A1101', 'J1506'):
            source = common_source.source_for('rome:' + code)
            self.assertTrue(
                any(row['kind'] == 'skill' for row in source['skills'].values())
            )
            self.assertTrue(
                any(row['kind'] == 'behaviour' for row in source['skills'].values())
            )

    def test_only_unambiguous_primary_title_exact_links_are_grouped(self):
        fiches = rome_search_catalog()['fiches']
        self.assertGreater(len(unified.pairs()), 300)
        for code, pair in unified.pairs().items():
            self.assertTrue(pair['mappings'])
            for mapping in pair['mappings']:
                self.assertEqual(mapping['relation'], 'skos:exactMatch')
                self.assertEqual(
                    normalize(mapping['label']), normalize(fiches[code]['label'])
                )
                self.assertEqual(mapping['escoUri'], pair['uri'])
            rows = unified.group_rows(
                [
                    unified.resolve_reference('rome:' + code, 'fr'),
                    unified.resolve_reference('esco:' + pair['uri'], 'fr'),
                ]
            )
            self.assertEqual(len(rows), 1)
        code = next(code for code in fiches if code not in unified.pairs())
        self.assertEqual(unified.canonical('rome:' + code), 'rome:' + code)

    def test_uncertain_or_ambiguous_links_never_authorise_a_group(self):
        from eures_beta.occupations.catalog import rome_catalog

        code = next(iter(unified.pairs()))
        pair = unified.pairs()[code]
        mapping = deepcopy(pair['mappings'][0])
        mapping['escoUri'] = next(
            uri for uri in occupation_index() if uri != pair['uri']
        )
        modified = deepcopy(rome_catalog())
        modified['mappings'].append(mapping)
        try:
            with patch(
                'eures_beta.occupations.unified.iter_artifact',
                return_value=iter(modified['mappings']),
            ):
                unified.pairs.cache_clear()
                unified.reverse_pairs.cache_clear()
                self.assertNotIn(code, unified.pairs())
        finally:
            unified.pairs.cache_clear()
            unified.reverse_pairs.cache_clear()

    def test_no_albert_configuration_still_offers_verified_skills_without_network(self):
        with (
            patch.object(albert_skills, 'enabled', return_value=False),
            patch.object(albert_skills, 'ask') as ask,
        ):
            card = common_suggestions.card(self.uri)
        self.assertFalse(card['generated'])
        self.assertEqual(card['shortlistMethod'], 'official_priority')
        self.assertTrue(card['behaviours'])
        self.assertTrue(
            all(row['skillUri'] in self.source['skills'] for row in card['keySkills'])
        )
        ask.assert_not_called()
        self.assertFalse(OccupationSkillSuggestion.objects.exists())

    def test_albert_cache_is_shared_by_roles_and_source_versioned(self):
        with (
            patch.object(albert_skills, 'enabled', return_value=True),
            patch.object(albert_skills, 'ask', return_value=self.keys) as ask,
        ):
            first = common_suggestions.card(self.uri)
            second = common_suggestions.card('esco:' + self.uri)
            self.assertEqual(first['keySkills'], second['keySkills'])
            ask.assert_called_once()
            self.assertEqual(OccupationSkillSuggestion.objects.get().status, 'ready')
            with patch.object(
                common_source, 'version', return_value='common-new-reviewed-source'
            ):
                common_suggestions.card(self.uri)
            self.assertEqual(ask.call_count, 2)
            self.assertEqual(OccupationSkillSuggestion.objects.count(), 2)

    def test_forged_model_identifiers_fail_closed_with_usable_official_fallback(self):
        with (
            patch.object(albert_skills, 'enabled', return_value=True),
            patch.object(albert_skills, 'ask', return_value=['invented']) as ask,
        ):
            card = common_suggestions.card(self.uri)
            again = common_suggestions.card(self.uri)
        self.assertTrue(card['unavailable'])
        self.assertFalse(card['generated'])
        self.assertEqual(card['keySkills'], again['keySkills'])
        self.assertEqual(ask.call_count, 1)
        self.assertFalse(
            OccupationSkillSuggestion.objects.filter(status='ready').exists()
        )
        self.assertTrue(
            all(row['skillUri'] in self.source['skills'] for row in card['keySkills'])
        )

    def test_candidate_and_employer_receive_the_same_choices_and_keep_role_guards(self):
        self.client.get('/candidate/prepare/?lang=fr')
        token = self.client.session[KEY]['token']
        endpoint = reverse('occupation_skill_suggestions')

        def api(role, **extra):
            return self.client.post(
                endpoint,
                json.dumps(
                    {'role': role, 'occupation': self.uri, 'language': 'fr', **extra}
                ),
                content_type='application/json',
            )

        with patch.object(albert_skills, 'enabled', return_value=False):
            candidate = api('candidate', token=token)
            self.assertEqual(candidate.status_code, 200)
            self.assertEqual(api('candidate', token='foreign').status_code, 403)
            self.assertEqual(api('employer').status_code, 403)
            employer = User.objects.create_user(
                'common-employer@example.invalid', kind='employer'
            )
            self.client.force_login(employer)
            response = api('employer')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(candidate.json()['skills'], response.json()['skills'])
            self.assertEqual(
                candidate.json()['behaviours'], response.json()['behaviours']
            )

    def test_rome_only_form_and_employer_save_rebuild_sources_without_inventing_ids(
        self,
    ):
        code = next(
            code
            for code in rome_search_catalog()['fiches']
            if code not in unified.pairs()
        )
        ref = 'rome:' + code
        source = common_source.source_for(ref)
        technical = common_source.balanced(source, 2)
        behaviours = common_source.ordered(source, 'behaviour')[:1]
        selection = {
            ref: {
                'skills': technical,
                'behaviours': behaviours,
                'sources': {'invented': 'official'},
            }
        }
        form = ProjectForm(
            answers(occupation_references=[ref], occupation_skills=selection)
        )
        self.assertTrue(form.is_valid(), form.errors)
        candidate = form.cleaned_data['occupation_skills']
        self.assertNotIn('invented', candidate[ref]['sources'])
        data = empty_data()
        data['title'] = 'Fictional position'
        data['occupation'] = {
            'version': '1.2.1',
            'title': data['title'],
            'language': 'fr',
            'uris': [],
            'rome_codes': [code],
            'personal': '',
        }
        data['occupationSkills'] = selection
        employer = clean_data(data)
        self.assertEqual(candidate, employer['occupationSkills'])
        for language in ('fr', 'en', 'de'):
            self.assertTrue(continuous.summary(candidate, language))

    def test_equivalent_occupation_aliases_share_limits_and_preserve_old_reference(
        self,
    ):
        code = next(iter(unified.pairs()))
        uri = unified.pairs()[code]['uri']
        source = common_source.source_for(uri)
        keys = common_source.balanced(source, 6)
        values = {uri: {'skills': keys[:3]}, 'rome:' + code: {'skills': keys[3:5]}}
        saved = continuous.validated_selection(values, [uri, 'rome:' + code])
        self.assertEqual(len(saved), 1)
        self.assertEqual(len(saved[uri]['skills']), 5)
        values['rome:' + code]['skills'] = keys[3:6]
        if len(keys) == 6:
            with self.assertRaises(ValueError):
                continuous.validated_selection(values, [uri, 'rome:' + code])

    def test_search_contract_uses_one_catalogue_in_three_languages_without_sources_on_labels(
        self,
    ):
        for language in ('fr', 'en', 'de'):
            response = self.client.post(
                '/api/occupations/',
                json.dumps({'unified': True, 'q': 'D1102', 'lang': language}),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            row = response.json()['unified_results'][0]
            self.assertTrue(row['description'])
            self.assertNotIn('ROME', row['label'])
            self.assertNotIn('ESCO', row['label'])
            self.assertEqual(len(row['references']), 2)

    def test_existing_selections_are_preserved_when_the_shortlist_changes(self):
        ref = 'rome:D1108'
        source = common_source.source_for(ref)
        technical = [
            key for key, row in source['skills'].items() if row['kind'] == 'skill'
        ]
        with patch.object(albert_skills, 'enabled', return_value=False):
            first = common_suggestions.card(ref)
            offered = {row['skillUri'] for row in first['keySkills']}
            previous = next(key for key in technical if key not in offered)
            second = common_suggestions.card(ref, selection={'skills': [previous]})
            self.assertIn(previous, {row['skillUri'] for row in second['keySkills']})
            with self.assertRaises(ValueError):
                common_suggestions.card(ref, selection={'skills': ['invented']})
        self.assertTrue(
            all(
                source['skills'][row['skillUri']].get('skillType') != 'knowledge'
                for row in first['keySkills']
            )
        )
