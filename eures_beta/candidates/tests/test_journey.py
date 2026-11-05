import time
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.html import strip_tags
from eures_beta.candidates.journey import KEY, SCHEMA, ConditionsForm, MobilityForm


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class CandidateJourneyTests(TestCase):
    def get(self, step=1, **query):
        return self.client.get(
            '/candidate/prepare/', {'step': step, **query}, secure=True
        )

    def post(self, step=1, **data):
        defaults = {
            1: {'desired_countries': ['FR']},
            2: {'mobility': 'discuss'},
            3: {
                'availability': 'discuss',
                'contract_types': ['discuss'],
                'working_time': ['discuss'],
                'working_conditions': ['discuss'],
                'schedule_preference': 'discuss',
                'salary_preference': 'discuss',
            },
            4: {'action': 'finish'},
        }
        return self.client.post(
            f'/candidate/prepare/?step={step}&lang=fr',
            {
                'action': 'continue',
                'token': self.client.session.get(KEY, {}).get('token', ''),
                **defaults[step],
                **data,
            },
            secure=True,
        )

    def advance(self):
        self.get()
        self.post(1, occupation_references=['rome:D1102'])
        self.post(2)

    def test_four_steps_without_upload_or_career_history(self):
        self.advance()
        self.post(3)
        self.assertContains(self.get(4), 'ROME D1102')
        self.assertEqual(
            self.post(4, display_name='Personne fictive', reviewed='on').status_code,
            302,
        )
        self.assertTrue(self.client.session[KEY]['confirmed'])
        for step in range(1, 5):
            response = self.get(step)
            for forbidden in (
                'type="file"',
                'multipart/form-data',
                'id_work_experience',
                'id_education',
                'id_skills',
                'id_driving_licences',
            ):
                self.assertNotContains(response, forbidden)
            # CSRF values may contain "CV"; only visible text is relevant here.
            self.assertNotIn('CV', strip_tags(response.content.decode()))
        self.assertEqual(
            self.client.get('/candidate/import/', secure=True).status_code, 404
        )

    def test_uploads_rejected_and_no_cv_action(self):
        self.get()
        self.assertEqual(
            self.post(
                document=SimpleUploadedFile('fiction.pdf', b'%PDF-fiction')
            ).status_code,
            400,
        )
        self.assertEqual(self.post(action='read').status_code, 400)
        self.assertEqual(self.post(action='without_cv').status_code, 400)

    def test_old_session_is_sanitised_and_project_retained(self):
        session = self.client.session
        session[KEY] = {
            'created_at': time.time(),
            'token': 'old-token',
            'unlocked': 5,
            'cv_text': 'Fictional CV text',
            'sources': {'skills': 'old'},
            'data': {
                'occupation_references': ['rome:D1102'],
                'desired_countries': ['LU'],
                'work_experience': 'old',
                'education': 'old',
                'skills': 'old',
                'languages': 'old',
                'driving_licences': 'old',
                'french_level': 'B1',
            },
        }
        session.save()
        response = self.get(3)
        self.assertRedirects(
            response,
            '/candidate/prepare/?step=1&lang=fr',
            fetch_redirect_response=False,
        )
        draft = self.client.session[KEY]
        self.assertEqual(draft['schema'], SCHEMA)
        self.assertEqual(draft['data']['occupation_references'], ['rome:D1102'])
        self.assertEqual(
            draft['data']['language_skills']['languages'],
            [{'code': 'fr', 'level': 'B1'}],
        )
        self.assertNotIn('french_level', draft['data'])
        for key in ('cv_text', 'sources', 'ocr'):
            self.assertNotIn(key, draft)
        for key in (
            'work_experience',
            'education',
            'skills',
            'languages',
            'driving_licences',
        ):
            self.assertNotIn(key, draft['data'])
        self.assertNotEqual(draft['token'], 'old-token')

    def test_independent_catalogue_search_and_forged_references(self):
        self.get()
        response = self.post(action='search', occupation_query='D1102')
        self.assertContains(response, 'rome:D1102')
        self.assertNotContains(response, 'value="esco:')
        self.assertEqual(
            self.post(occupation_references=['rome:INVALID']).status_code, 200
        )
        self.assertEqual(
            self.post(occupation_references=['rome:D1102']).status_code, 302
        )

    def test_multi_catalogue_selection_survives_language_change(self):
        from eures_beta.candidates.occupation_choices import search_occupations

        esco = next(
            row['value']
            for row in search_occupations('boulanger', 'fr')
            if row['value'].startswith('esco:')
        )
        self.get()
        self.assertEqual(
            self.post(occupation_references=[esco, 'rome:D1102']).status_code, 302
        )
        response = self.get(1, lang='de')
        self.assertContains(response, esco)
        self.assertContains(response, 'rome:D1102')

    def test_weekly_schedule_validation_storage_and_review(self):
        self.advance()
        response = self.post(3, schedule_preference='specific')
        self.assertIn('schedule_preference', response.context['form'].errors)
        response = self.post(
            3,
            schedule_preference='specific',
            schedule_monday=['morning', 'afternoon'],
            schedule_saturday=['evening'],
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session[KEY]['data']['schedule_monday'],
            ['morning', 'afternoon'],
        )
        self.assertContains(self.get(4), 'Lundi')
        self.assertContains(self.get(4), 'Après-midi')
        self.assertEqual(
            self.post(
                3, schedule_preference='specific', schedule_monday=['invalid']
            ).status_code,
            200,
        )
        self.post(3, schedule_preference='varied', schedule_monday=['morning'])
        self.assertEqual(self.client.session[KEY]['data']['schedule_monday'], [])

    def test_commuting_choices_are_conditional_and_do_not_infer_licences(self):
        self.assertFalse(MobilityForm({'mobility': 'commute'}).is_valid())
        self.assertFalse(
            MobilityForm(
                {
                    'mobility': 'commute',
                    'commute_time': '1h',
                    'transport_modes': ['car', 'discuss'],
                }
            ).is_valid()
        )
        form = MobilityForm(
            {'mobility': 'commute', 'commute_time': '1h', 'transport_modes': ['car']}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['licences_held'], [])
        self.assertFalse(
            MobilityForm(
                {'mobility': 'discuss', 'licences_held': ['none', 'B']}
            ).is_valid()
        )
        self.assertTrue(
            MobilityForm({'mobility': 'move', 'commute_time': 'invalid'}).is_valid()
        )

    def test_salary_date_and_choice_validation(self):
        base = {
            'availability': 'discuss',
            'contract_types': ['permanent'],
            'working_time': ['full'],
            'working_conditions': ['day'],
            'schedule_preference': 'discuss',
            'salary_preference': 'discuss',
        }
        self.assertTrue(ConditionsForm(base).is_valid())
        for change in (
            {'availability': 'date'},
            {'working_conditions': ['night', 'none']},
            {'contract_types': ['permanent', 'discuss']},
            {'salary_preference': 'minimum'},
        ):
            self.assertFalse(ConditionsForm({**base, **change}).is_valid())
        self.advance()
        self.assertEqual(
            self.post(
                3,
                salary_preference='minimum',
                salary_amount='2300.50',
                salary_currency='EUR',
                salary_period='month',
                salary_basis='gross',
            ).status_code,
            302,
        )
        self.assertEqual(self.client.session[KEY]['data']['salary_amount'], '2300.50')

    def test_access_csrf_and_token(self):
        self.assertEqual(self.client.get('/candidate/prepare/').status_code, 404)
        with override_settings(DEMO_MODE=False):
            self.assertEqual(self.get().status_code, 404)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post('/candidate/prepare/', {}, secure=True).status_code, 403
        )
        self.get()
        self.assertEqual(self.post(token='wrong').status_code, 400)

    def test_isolation_expiration_discard_step_order_and_escaping(self):
        self.get()
        token = self.client.session[KEY]['token']
        other = Client()
        other.get('/candidate/prepare/', secure=True)
        self.assertNotEqual(token, other.session[KEY]['token'])
        self.assertEqual(self.get(4).status_code, 302)
        self.post(desired_occupations='<script>alert(1)</script>')
        self.post(2)
        self.post(3)
        self.assertContains(self.get(4), '&lt;script&gt;')
        self.assertNotContains(self.get(4), '<script>alert(1)</script>')
        self.post(4, action='discard')
        self.assertNotIn(KEY, self.client.session)
        self.get()
        session = self.client.session
        session[KEY] = {
            **session[KEY],
            'created_at': time.time() - 1801,
            'touched_at': time.time() - 1801,
        }
        expired_token = session[KEY]['token']
        session.save()
        self.assertNotEqual(self.get().context['draft']['token'], expired_token)

    def test_languages_and_legacy_link_start_at_project(self):
        for lang, title in [
            ('fr', 'Mon projet'),
            ('en', 'My project'),
            ('de', 'Mein Vorhaben'),
        ]:
            response = self.get(lang=lang)
            self.assertContains(response, title)
            self.assertContains(response, f'<html lang="{lang}">')
        response = self.get(without_cv='1')
        self.assertRedirects(
            response,
            '/candidate/prepare/?step=1&lang=fr',
            fetch_redirect_response=False,
        )

    def test_dynamic_languages_are_validated_saved_and_reviewed(self):
        import json

        self.get()
        self.post(occupation_references=['rome:D1102'])
        declaration = {
            'status': 'specified',
            'languages': [
                {'code': 'fr', 'level': 'B1'},
                {'code': 'pt', 'level': 'B2'},
                {'code': 'lb', 'level': 'A2'},
            ],
        }
        response = self.post(2, language_skills=json.dumps(declaration))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session[KEY]['data']['language_skills'], declaration
        )
        response = self.get(2, lang='de')
        self.assertContains(response, '/static/employer/language-fields.js')
        self.assertNotContains(response, 'id_french_level')
        self.post(3)
        review = self.get(4)
        self.assertContains(review, 'data-language-code="pt"')
        self.assertContains(review, 'B2')
        self.assertNotContains(review, "'status': 'specified'")
        self.post(2, language_skills=json.dumps({'status': 'discuss', 'languages': []}))
        self.assertEqual(
            self.client.session[KEY]['data']['language_skills'],
            {'status': 'discuss', 'languages': []},
        )

    def test_invalid_duplicate_and_incomplete_language_rows_are_rejected(self):
        from eures_beta.candidates.language_choices import LanguageSkillsField
        from django.core.exceptions import ValidationError

        field = LanguageSkillsField()
        for value in [
            {'status': 'specified', 'languages': [{'code': 'zz', 'level': 'B1'}]},
            {'status': 'specified', 'languages': [{'code': 'fr', 'level': ''}]},
            {'status': 'specified', 'languages': [{'code': 'fr', 'level': 'native'}]},
            {'status': 'discuss', 'languages': [{'code': 'fr', 'level': 'B1'}]},
            {'status': 'specified', 'languages': [{'code': 'fr', 'level': 'B1'}] * 2},
            {
                'status': 'specified',
                'languages': [{'code': 'fr', 'level': 'B1', 'label': 'forged'}],
            },
            {'status': 'specified', 'languages': [None]},
        ]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value)
        self.assertEqual(field.clean(None), {'status': 'unspecified', 'languages': []})

    def test_old_language_answers_keep_exact_levels_without_inventing_equivalence(self):
        from eures_beta.candidates.language_choices import upgrade_language_answers

        data = {
            'french_level': 'native',
            'english_level': 'B1',
            'german_level': 'discuss',
        }
        upgrade_language_answers(data)
        self.assertEqual(
            data['language_skills']['languages'], [{'code': 'en', 'level': 'B1'}]
        )
        self.assertEqual(
            data['language_notes'],
            [{'code': 'fr', 'value': 'native'}, {'code': 'de', 'value': 'discuss'}],
        )
        self.assertNotIn('french_level', data)
        self.assertTrue(
            MobilityForm({'mobility': 'discuss', 'language_discuss': 'on'}).is_valid()
        )

    def test_availability_only_suggests_timing_and_exclusive_conflicts_are_checked(
        self,
    ):
        from eures_beta.candidates.schedule_rules import (
            suggested_conditions,
            inconsistent_conditions,
        )

        data = {
            'schedule_preference': 'specific',
            'schedule_monday': ['morning'],
            'schedule_saturday': ['night'],
            'working_conditions': ['day', 'night', 'weekend'],
        }
        self.assertEqual(suggested_conditions(data), ['day', 'night', 'weekend'])
        self.assertNotIn('physical', suggested_conditions(data))
        self.assertEqual(inconsistent_conditions(data), [])
        restricted = {**data, 'schedule_saturday': [], 'schedule_strict': True}
        self.assertEqual(inconsistent_conditions(restricted), ['night', 'weekend'])
        self.assertEqual(
            inconsistent_conditions({**restricted, 'schedule_strict': False}), []
        )
        self.advance()
        response = self.post(
            3,
            schedule_preference='specific',
            schedule_monday=['morning'],
            schedule_strict='on',
            working_conditions=['night'],
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('working_conditions', response.context['form'].errors)
        response = self.post(
            3,
            schedule_preference='specific',
            schedule_monday=['morning'],
            working_conditions=['night'],
        )
        self.assertEqual(response.status_code, 302)

    def test_condition_overrides_are_preserved_and_invalid_suggestion_state_is_rejected(
        self,
    ):
        import json

        self.advance()
        response = self.post(
            3,
            schedule_preference='specific',
            schedule_monday=['morning'],
            working_conditions=['standing'],
            condition_overrides=json.dumps(['day']),
        )
        self.assertEqual(response.status_code, 302)
        draft = self.client.session[KEY]['data']
        self.assertEqual(draft['condition_overrides'], ['day'])
        self.assertEqual(draft['working_conditions'], ['standing'])
        response = self.post(3, condition_overrides=json.dumps(['physical']))
        self.assertEqual(response.status_code, 200)
        self.assertIn('condition_overrides', response.context['form'].errors)


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class CandidateJourneyAccessibilityTests(TestCase):
    """Fixes from the 4 November 2026 accessibility and fluency review."""

    get = CandidateJourneyTests.get
    post = CandidateJourneyTests.post
    advance = CandidateJourneyTests.advance

    def reach_review(self):
        self.advance()
        self.post(3)
        return self.get(4)

    def test_page_title_names_each_step_and_errors(self):
        self.get()
        self.assertContains(
            self.get(1, lang='fr'),
            '<title>Étape 1 sur 4 : Mon projet — Parcours candidat — Match Europe</title>',
        )
        response = self.post(1, desired_countries=[])
        self.assertContains(response, '<title>Erreur — Étape 1 sur 4 : Mon projet')
        self.assertContains(
            self.get(1, lang='de'), '<title>Schritt 1 von 4: Mein Vorhaben'
        )

    def test_error_summary_lists_and_links_each_error(self):
        self.get()
        response = self.post(1, desired_countries=[])
        self.assertContains(response, 'id="journey-error-summary"')
        self.assertContains(response, '2 erreurs à corriger')
        self.assertContains(response, 'href="#id_occupation_query"')
        self.assertContains(response, 'href="#id_desired_countries_0"')
        self.assertContains(response, 'aria-describedby="id_desired_countries_error"')
        self.assertContains(response, 'id="id_desired_countries_error"')
        page = response.content.decode()
        self.assertLess(
            page.index('href="#id_occupation_query"'),
            page.index('href="#id_desired_countries_0"'),
        )
        self.assertNotContains(self.get(1), 'id="journey-error-summary"')

    def test_search_does_not_show_error_summary(self):
        self.get()
        response = self.post(
            1, action='search', occupation_query='zz', desired_countries=[]
        )
        self.assertNotContains(response, 'id="journey-error-summary"')

    def test_conditionally_required_questions_are_marked(self):
        self.get()
        self.assertContains(
            self.get(1), 'Les métiers que je souhaite exercer (obligatoire)'
        )
        self.post(1, occupation_references=['rome:D1102'])
        page = self.get(2).content.decode()
        for label in (
            'Temps de trajet maximum à l’aller (obligatoire)',
            'Comment pourriez-vous vous rendre au travail ? (obligatoire)',
        ):
            self.assertIn(label, page)

    def test_contact_fields_identify_their_purpose(self):
        page = self.reach_review()
        self.assertContains(page, 'autocomplete="name"')
        self.assertContains(page, 'autocomplete="email"')

    def test_draft_expiry_counts_from_last_activity(self):
        self.get()
        session = self.client.session
        token = session[KEY]['token']
        session[KEY] = {
            **session[KEY],
            'created_at': time.time() - 3600,
            'touched_at': time.time() - 60,
        }
        session.save()
        response = self.get()
        self.assertEqual(response.context['draft']['token'], token)
        self.assertFalse(response.context['expired'])
        self.assertGreater(self.client.session[KEY]['touched_at'], time.time() - 5)

    def test_expiry_warning_offers_to_extend(self):
        response = self.get()
        self.assertContains(response, 'id="journey-timeout"')
        self.assertContains(response, 'data-seconds="1800"')
        self.assertContains(response, 'data-warning-seconds="120"')
        self.assertContains(response, 'Garder mon brouillon 30 minutes de plus')

    def test_editing_from_review_returns_to_review(self):
        page = self.reach_review()
        self.assertContains(page, '?step=1&amp;lang=fr&amp;return=review')
        self.assertContains(page, 'Modifier : Mon projet')
        self.assertNotContains(page, 'Modifier cette rubrique')
        edit = self.get(1, lang='fr', **{'return': 'review'})
        self.assertContains(edit, 'name="return" value="review"')
        self.assertContains(edit, 'Enregistrer et revenir au récapitulatif')
        response = self.post(
            1, occupation_references=['rome:D1102'], **{'return': 'review'}
        )
        self.assertRedirects(
            response,
            '/candidate/prepare/?step=4&lang=fr',
            fetch_redirect_response=False,
        )
        response = self.post(1, occupation_references=['rome:D1102'])
        self.assertRedirects(
            response,
            '/candidate/prepare/?step=2&lang=fr',
            fetch_redirect_response=False,
        )

    def test_return_to_review_ignored_before_review_is_unlocked(self):
        self.get()
        edit = self.get(1, **{'return': 'review'})
        self.assertNotContains(edit, 'name="return" value="review"')
        response = self.post(
            1, occupation_references=['rome:D1102'], **{'return': 'review'}
        )
        self.assertRedirects(
            response,
            '/candidate/prepare/?step=2&lang=fr',
            fetch_redirect_response=False,
        )

    def test_extend_keeps_the_existing_draft_and_answers(self):
        self.advance()
        before = self.client.session[KEY]
        response = self.post(3, action='extend')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'extended': True, 'seconds': 1800})
        after = self.client.session[KEY]
        for name in ('token', 'data', 'unlocked', 'created_at'):
            self.assertEqual(after[name], before[name])
        self.assertGreaterEqual(after['touched_at'], before['touched_at'])

    def test_extend_refuses_expired_or_missing_draft(self):
        self.advance()
        session = self.client.session
        session[KEY]['touched_at'] = time.time() - 1801
        session.save()
        response = self.post(3, action='extend')
        self.assertEqual(response.status_code, 409)
        self.assertNotIn(KEY, self.client.session)
        self.assertEqual(self.post(1, action='extend').status_code, 409)
        self.assertNotIn(KEY, self.client.session)

    def test_extend_requires_the_current_draft_token_and_csrf(self):
        self.get()
        self.assertEqual(self.post(action='extend', token='wrong').status_code, 400)
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.client.cookies
        self.assertEqual(
            client.post(
                '/candidate/prepare/?lang=fr',
                {'action': 'extend', 'token': self.client.session[KEY]['token']},
                secure=True,
            ).status_code,
            403,
        )
