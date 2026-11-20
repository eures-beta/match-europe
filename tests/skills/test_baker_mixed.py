import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from eures_beta.skills import baker_mixed, continuous, albert_skills, common_source
from eures_beta.candidates import registration
from eures_beta.candidates.forms import ProjectForm, KEY
from tests.candidates.test_registration import answers


class BakerMixedTests(TestCase):
    def setUp(self):
        self.data = baker_mixed.catalogue()
        self.uri = baker_mixed.URI
        self.selection = {
            self.uri: {
                'skills': [self.data['skills'][3]['id'], 'rome:competence:490153'],
                'behaviours': [
                    next(
                        x['id']
                        for x in self.data['behaviours']
                        if x['labels']['en'] == 'work independently'
                    )
                ],
            }
        }

    def project(self, references=None, selection=None):
        return answers(
            occupation_references=references or ['rome:D1102'],
            occupation_skills=selection or self.selection,
        )

    def test_both_occupation_references_accept_and_preserve_identical_selection(self):
        for references in (
            ['rome:D1102'],
            ['esco:' + self.uri],
            ['rome:D1102', 'esco:' + self.uri],
        ):
            form = ProjectForm(self.project(references))
            self.assertTrue(form.is_valid(), form.errors)
            value = form.cleaned_data['occupation_skills'][self.uri]
            self.assertEqual(value['skills'], self.selection[self.uri]['skills'])
            self.assertEqual(value['version'], common_source.version())
            self.assertEqual(
                value['sources']['rome:competence:490153'][0]['id'],
                'rome:competence:490153',
            )
            self.assertEqual(len(form.cleaned_data['occupation_skills']), 1)

    def test_provenance_is_rebuilt_and_foreign_excess_duplicate_selections_rejected(
        self,
    ):
        for group, ids in (
            ('skills', ['rome:competence:invented']),
            ('skills', [x['id'] for x in self.data['skills'][:6]]),
            ('skills', [self.data['skills'][0]['id']] * 2),
            ('behaviours', [x['id'] for x in self.data['behaviours'][:4]]),
            ('skills', [self.data['behaviours'][0]['id']]),
        ):
            form = ProjectForm(self.project(selection={self.uri: {group: ids}}))
            self.assertFalse(form.is_valid())
            self.assertIn('occupation_skills', form.errors)
        with self.assertRaises(ValueError):
            continuous.validated_selection(self.selection, [], mixed=True)
        self.selection[self.uri]['sources'] = {'forged': 'official'}
        value = continuous.validated_selection(
            self.selection, [baker_mixed.ROME], mixed=True
        )
        self.assertNotIn('forged', value[self.uri]['sources'])

    def test_registration_profile_update_summary_in_three_languages(self):
        for language in ('fr', 'en', 'de'):
            data = self.project()
            pending = registration.create_request(
                'baker-' + language + '@example.invalid', data, language
            )
            user = registration.confirm_registration(
                registration.token_for(pending)
            ).user
            profile = user.candidate_profile
            profile.refresh_from_db()
            self.assertEqual(
                profile.occupation_skills[self.uri]['skills'],
                self.selection[self.uri]['skills'],
            )
            self.assertEqual(profile.occupation_references, ['rome:D1102'])
            text = continuous.summary(profile.occupation_skills, language)
            label = next(
                x['labels'][language]
                for x in self.data['skills']
                if x['id'] == 'rome:competence:490153'
            )
            self.assertIn(label, text)
            registration.update_profile(user, data, language)
            self.client.force_login(user)
            self.assertContains(
                self.client.get('/candidate/profile/?lang=' + language), label
            )

    def test_api_returns_same_choices_for_rome_and_esco_without_albert(self):
        self.client.get('/candidate/prepare/?lang=fr')
        token = self.client.session[KEY]['token']
        with patch.object(albert_skills, 'ask') as ask:
            for reference in (self.uri, 'rome:D1102'):
                response = self.client.post(
                    reverse('occupation_skill_suggestions'),
                    json.dumps(
                        {
                            'role': 'candidate',
                            'occupation': reference,
                            'language': 'fr',
                            'token': token,
                        }
                    ),
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertTrue(result['mixed'])
                self.assertEqual(len(result['skills']), 13)
                self.assertEqual(
                    len(result['skills']), len({x[0] for x in result['skills']})
                )
                self.assertIn('rome:competence:490153', result['provenance'])
            ask.assert_not_called()
        self.assertEqual(
            self.client.post(
                reverse('occupation_skill_suggestions'),
                '{}',
                content_type='application/json',
            ).status_code,
            400,
        )
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(
                reverse('occupation_skill_suggestions'),
                '{}',
                content_type='application/json',
            )
            .status_code,
            403,
        )

    def test_shared_entries_and_rome_evidence_are_traceable(self):
        ids = [x['id'] for group in ('skills', 'behaviours') for x in self.data[group]]
        self.assertEqual(len(ids), len(set(ids)))
        evidence = {
            str(x['code_ogr'])
            for kind in self.data['romeEvidence'].values()
            for groups in kind.values()
            for group in groups
            for x in group['items']
        }
        for group in ('skills', 'behaviours'):
            for row in self.data[group]:
                self.assertTrue(all(row['labels'][lang] for lang in ('fr', 'en', 'de')))
                for source in row['sources']:
                    if source['scheme'] == 'ROME':
                        self.assertIn(source['id'], evidence)
        self.assertEqual(
            len([x for x in self.data['skills'] if len(x['sources']) > 1]), 6
        )

    def test_baker_uses_the_same_common_validation_for_employer_and_candidate(self):
        self.assertIsNone(baker_mixed.card('rome:D1101'))
        self.assertEqual(len(continuous.reference_card(self.uri)['keySkills']), 8)
        self.assertEqual(
            continuous.validated_selection(self.selection, [self.uri]),
            continuous.validated_selection(self.selection, [self.uri], mixed=True),
        )

    def test_candidate_search_groups_only_reviewed_pair_without_visible_catalogue_names(
        self,
    ):
        from eures_beta.candidates.occupation_choices import (
            search_occupations,
            resolve_reference,
        )

        for lang, query in [('fr', 'boulanger'), ('en', 'baker'), ('de', 'Bäcker')]:
            rows = search_occupations(query, lang)
            baker = [row for row in rows if row['groupKey'] == self.uri]
            self.assertEqual(len(baker), 1)
            self.assertEqual(
                set(baker[0]['references']), {'esco:' + self.uri, baker_mixed.ROME}
            )
            self.assertEqual(
                baker[0]['description'], self.data['candidateDescription'][lang]
            )
            self.assertTrue(
                all(
                    'ESCO' not in row['label'] and 'ROME' not in row['label']
                    for row in rows
                )
            )
            by_code = search_occupations('D1102', lang)
            self.assertEqual(by_code[0]['description'], baker[0]['description'])
        other = resolve_reference('rome:D1108', 'fr')
        self.assertNotEqual(other['groupKey'], self.uri)

    def test_candidate_search_api_and_existing_rome_selection_share_one_card(self):
        response = self.client.post(
            '/api/occupations/',
            json.dumps({'candidate': True, 'q': 'boulanger', 'lang': 'fr'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(
                [
                    x
                    for x in response.json()['candidate_results']
                    if x['groupKey'] == self.uri
                ]
            ),
            1,
        )
        form = ProjectForm(self.project(['rome:D1102', 'esco:' + self.uri]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            len([x for x in form.reference_rows if x['groupKey'] == self.uri]),
            1,
        )
        self.assertIn('rome:D1102', form.cleaned_data['occupation_references'])

    def test_all_rome_fiches_have_original_descriptions_and_bakery_translations(self):
        from eures_beta.occupations.descriptions import catalogue, description
        from eures_beta.occupations.catalog import rome_search_catalog
        from eures_beta.candidates.occupation_choices import resolve_reference

        definitions = catalogue()
        self.assertEqual(set(definitions), set(rome_search_catalog()['fiches']))
        self.assertEqual(len(definitions), 1923)
        self.assertTrue(all(text.strip() for text in definitions.values()))
        for code in ('D1108', 'H2108'):
            for lang in ('fr', 'en', 'de'):
                row = resolve_reference('rome:' + code, lang)
                self.assertTrue(row['description'])
                self.assertEqual(row['descriptionLanguage'], lang)
        self.assertEqual(description('A1101', 'de')[1], 'fr')

    def test_official_exact_mapping_is_required_and_recorded_without_skill_equivalence(
        self,
    ):
        from copy import deepcopy
        from eures_beta.occupations.catalog import rome_catalog
        from eures_beta.candidates.occupation_choices import resolve_reference

        mapping = baker_mixed.official_mapping()
        self.assertEqual(mapping['id'], '11573')
        self.assertEqual(mapping['relation'], 'skos:exactMatch')
        saved = continuous.validated_selection(
            self.selection, [baker_mixed.ROME], mixed=True
        )
        self.assertEqual(saved[self.uri]['occupationMappings'][0], mapping)
        rows = deepcopy(rome_catalog())
        for row in rows['mappings']:
            if row['escoUri'] == self.uri and row['id'] == '11573':
                row['relation'] = 'skos:closeMatch'
        from eures_beta.occupations import unified

        try:
            with (
                patch('eures_beta.occupations.catalog.rome_catalog', return_value=rows),
                patch(
                    'eures_beta.occupations.unified.iter_artifact',
                    side_effect=lambda *args: iter(rows['mappings']),
                ),
            ):
                unified.pairs.cache_clear()
                unified.reverse_pairs.cache_clear()
                self.assertIsNone(baker_mixed.official_mapping())
                self.assertIsNone(baker_mixed.card(baker_mixed.ROME))
                self.assertEqual(
                    resolve_reference(baker_mixed.ROME, 'fr')['groupKey'],
                    baker_mixed.ROME,
                )
                with self.assertRaises(ValueError):
                    continuous.validated_selection(
                        self.selection, [baker_mixed.ROME], mixed=True
                    )
        finally:
            unified.pairs.cache_clear()
            unified.reverse_pairs.cache_clear()
