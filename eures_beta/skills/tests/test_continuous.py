import json
from time import time
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from eures_beta.skills import continuous, albert_skills
from eures_beta.skills.skills_pilot import catalogue
from eures_beta.occupations.catalog import catalog, occupation_index
from eures_beta.skills.models import OccupationSkillSuggestion
from eures_beta.candidates.journey import KEY, TTL, ProjectForm, ContactForm
from eures_beta.candidates.tests.test_registration import answers
from eures_beta.candidates import registration
from eures_beta.candidates.models import CandidateProfile
from eures_beta.users.models import User
from eures_beta.employers.employer_api import clean_data
from eures_beta.employers.offer_ingestion import ImportFailure, empty_data
from eures_beta.employers.models import JobOffer, Company, CompanyMembership


@override_settings(
    CONTINUOUS_SKILLS_ENABLED=True,
    SKILLS_ALBERT_ENABLED=True,
    SKILLS_ALBERT_SIMULATED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class ContinuousTests(TestCase):
    def setUp(self):
        self.cards, self.skills = catalogue()
        self.card = self.cards['restauration']
        self.uri = self.card['occupation']['uri']
        self.values = {
            self.uri: {
                'skills': [item['skillUri'] for item in self.card['keySkills'][:2]],
                'behaviours': [self.card['behaviours'][0]['skillUri']],
            }
        }
        self.endpoint = reverse('occupation_skill_suggestions')

    def employer(self):
        person = User.objects.create_user('employer@example.invalid', kind='employer')
        self.client.force_login(person)
        session = self.client.session
        session['employer_verified_email'] = person.email
        session.save()
        return person

    def api(self, role='candidate', uri=None, **extra):
        return self.client.post(
            self.endpoint,
            data=json.dumps(
                {'role': role, 'occupation': uri or self.uri, 'language': 'fr', **extra}
            ),
            content_type='application/json',
        )

    def candidate(self):
        person, _ = User.objects.get_or_create(
            email='candidate@example.invalid', defaults={'kind': 'candidate'}
        )
        self.client.force_login(person)
        self.client.get('/candidate/prepare/?lang=fr')
        return self.client.session[KEY]['token']

    def test_employer_workspace_is_remote_and_uses_real_account_authentication(self):
        self.employer()
        session = self.client.session
        session.pop('employer_verified_email', None)
        session.save()
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                ),
            ):
                for url in ('/employer/offers/', '/employer/connected/'):
                    self.assertEqual(
                        self.client.get(url, REMOTE_ADDR='192.0.2.1').status_code, 200
                    )

    def test_fifty_cards_are_shared_and_do_not_call_albert(self):
        token = self.candidate()
        with patch.object(albert_skills, 'ask') as ask:
            for card in self.cards.values():
                response = self.api(uri=card['occupation']['uri'], token=token)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()['skills']), 8)
                self.assertFalse(response.json()['generated'])
            ask.assert_not_called()
        self.assertFalse(OccupationSkillSuggestion.objects.exists())

    def test_unknown_to_shortlist_uses_verified_source_and_shared_cache(self):
        uri = next(
            uri
            for uri in occupation_index()
            if uri not in {card['occupation']['uri'] for card in self.cards.values()}
        )
        linked = {key: 'essential' for key in list(self.skills)[:8]}
        with (
            patch.object(
                albert_skills, 'source_for', return_value=(self.skills, linked)
            ),
            patch('eures_beta.integrations.albert.build_opener') as network,
        ):
            token = self.candidate()
            response = self.api(uri=uri, token=token)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['simulated'])
            self.employer()
            self.assertEqual(self.api('employer', uri).status_code, 200)
            self.assertEqual(OccupationSkillSuggestion.objects.count(), 1)
            network.assert_not_called()

    def test_role_session_expiry_csrf_and_network_guards(self):
        self.assertEqual(self.api().status_code, 403)
        token = self.candidate()
        self.assertEqual(self.api(token=token + 'wrong').status_code, 403)
        self.assertEqual(self.api('employer').status_code, 403)
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(self.endpoint, '{}', content_type='application/json')
            .status_code,
            403,
        )
        self.assertEqual(self.client.get(self.endpoint).status_code, 405)
        with override_settings(CONTINUOUS_SKILLS_ENABLED=False):
            self.assertEqual(self.api(token=token).status_code, 404)
        session = self.client.session
        draft = session[KEY]
        draft['touched_at'] = time() - TTL - 1
        session[KEY] = draft
        session.save()
        self.assertEqual(self.api(token=token).status_code, 403)

    def test_remote_suggestions_in_every_environment_preserve_role_guards(self):
        token = self.candidate()
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment, EMAIL_DELIVERY_ENABLED=True
                ),
            ):
                payload = {
                    'role': 'candidate',
                    'occupation': self.uri,
                    'language': 'fr',
                    'token': token,
                }
                response = self.client.post(
                    self.endpoint,
                    json.dumps(payload),
                    content_type='application/json',
                    REMOTE_ADDR='192.0.2.1',
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.api('employer').status_code, 403)

    def test_forged_foreign_duplicate_and_excessive_answers_rejected(self):
        for value in (
            [],
            {'unknown': {'skills': []}},
            {self.uri: {'skills': ['unknown']}},
            {self.uri: {'skills': self.values[self.uri]['skills'] * 2}},
            {
                self.uri: {
                    'skills': [item['skillUri'] for item in self.card['keySkills'][:6]]
                }
            },
            {self.uri: {'behaviours': ['unknown']}},
        ):
            with self.assertRaises(ValueError):
                continuous.validated_selection(value, [self.uri])
        with self.assertRaises(ValueError):
            continuous.validated_selection(self.values, [])

    def project(self):
        data = answers()
        data.update(
            occupation_references=['esco:' + self.uri], occupation_skills=self.values
        )
        return data

    def test_candidate_registration_edit_and_profile_preserve_ids_and_labels(self):
        for lang in ('fr', 'en', 'de'):
            data = self.project()
            pending = registration.create_request(
                'candidate-' + lang + '@example.invalid', data, lang
            )
            user = registration.confirm_registration(
                registration.token_for(pending)
            ).user
            registration.update_profile(user, data, lang)
            self.assertEqual(
                user.candidate_profile.occupation_skills[self.uri]['skills'],
                self.values[self.uri]['skills'],
            )
            self.client.force_login(user)
            page = self.client.get('/candidate/profile/?lang=' + lang)
            self.assertNotContains(page, '<strong>None</strong>')
            self.assertContains(
                page, self.skills[self.values[self.uri]['skills'][0]]['labels'][lang]
            )
            self.assertEqual(
                self.client.post('/candidate/profile/edit/').status_code, 302
            )
            review = self.client.get('/candidate/prepare/?step=4&lang=' + lang)
            self.assertContains(
                review, self.skills[self.values[self.uri]['skills'][0]]['labels'][lang]
            )
            data['occupation_skills'] = {
                self.uri: {'skills': self.values[self.uri]['skills'][:1]}
            }
            updated = registration.update_profile(user, data, lang)
            self.assertEqual(
                updated.occupation_skills[self.uri]['skills'],
                self.values[self.uri]['skills'][:1],
            )

    def test_candidate_journey_post_and_language_switch_keep_declarations(self):
        token = self.candidate()
        payload = {
            'token': token,
            'action': 'continue',
            'project_mode': 'occupation',
            'occupation_references': ['esco:' + self.uri],
            'occupation_skills': json.dumps(self.values),
            'desired_countries': ['FR'],
        }
        self.assertEqual(
            self.client.post('/candidate/prepare/?lang=fr', payload).status_code, 302
        )
        self.assertEqual(
            self.client.session[KEY]['data']['occupation_skills'][self.uri]['skills'],
            self.values[self.uri]['skills'],
        )
        payload['target_language'] = 'de'
        self.assertEqual(
            self.client.post('/candidate/prepare/?step=1&lang=fr', payload).status_code,
            302,
        )
        page = self.client.get('/candidate/prepare/?step=1&lang=de')
        self.assertContains(page, 'data-occupation-skills')
        self.assertContains(page, self.values[self.uri]['skills'][0])

    def test_return_to_open_project_clears_only_occupation_declarations(self):
        from eures_beta.candidates.tests.test_skill_project import project

        data = answers()
        data.update(project())
        data['occupation_skills'] = self.values
        form = ProjectForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['occupation_skills'], {})
        self.assertTrue(form.cleaned_data['acquired_skills'])

    def test_employer_save_reload_edit_duplicate_and_foreign_access(self):
        person = self.employer()
        company = Company.objects.create(name='Fictional employer')
        CompanyMembership.objects.create(company=company, person=person)
        data = empty_data()
        data.update(
            title='Serveur',
            occupation={
                'language': 'fr',
                'version': catalog()['manifest']['version'],
                'title': 'Serveur',
                'uris': [self.uri],
            },
            occupationSkills=self.values,
        )
        data = clean_data(data)
        offer = JobOffer.objects.create(
            company=company,
            created_by=person,
            session_key='',
            email=person.email,
            contact={'name': 'Fictional contact', 'email': person.email},
            data=data,
            source_kind='manual',
            preparation_agreed_at=timezone.now(),
        )
        from eures_beta.employers.employer_workspace import OfferEditForm

        form = OfferEditForm(offer=offer)
        payload = {field.name: field.value() or '' for field in form}
        for key in ('workConditions', 'permits', 'arrivalAids'):
            payload[key] = payload[key] or []
        payload.update(
            {'contact-name': 'Fictional contact', 'contact-email': person.email}
        )
        response = self.client.post(
            reverse('employer_offer_edit', args=[offer.pk]), payload
        )
        self.assertEqual(response.status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(
            offer.data['occupationSkills'][self.uri]['skills'],
            self.values[self.uri]['skills'],
        )
        page = self.client.get(reverse('employer_offer', args=[offer.pk]))
        self.assertContains(
            page, self.skills[self.values[self.uri]['skills'][0]]['labels']['fr']
        )
        self.assertEqual(
            self.client.post(
                reverse('employer_offer_duplicate', args=[offer.pk]),
                {'revision': str(offer.revision)},
            ).status_code,
            302,
        )
        copy = JobOffer.objects.exclude(pk=offer.pk).get()
        self.assertEqual(copy.data['occupationSkills'], offer.data['occupationSkills'])
        outsider = User.objects.create_user('outsider@example.invalid', kind='employer')
        self.client.force_login(outsider)
        session = self.client.session
        session['employer_verified_email'] = outsider.email
        session.save()
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 404
        )
        data['occupationSkills'] = {'invented': {'skills': []}}
        with self.assertRaises(ImportFailure):
            clean_data(data)

    def test_real_address_is_accepted_without_browser_confirmation_shortcut(self):
        form = ContactForm(
            {
                'display_name': 'Fictional',
                'contact_email': 'candidate@example.org',
                'reviewed': True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            self.client.post('/candidate/registration/local-confirmation/').status_code,
            404,
        )

    @override_settings(ALBERT_IMPORT_ENABLED=True, ALBERT_IMPORT_SIMULATED=True)
    @patch('eures_beta.integrations.albert.build_opener')
    def test_offer_structuring_simulation_never_calls_albert(self, opener):
        from eures_beta.employers.offer_structuring import structure

        self.assertEqual(
            structure('Serveur\nMissions : accueillir les clients')['extraction'],
            'albert_simulated',
        )
        opener.assert_not_called()

    @override_settings(TEST_ACCOUNTS_ENABLED=True)
    def test_test_account_can_reopen_own_unassigned_offer_from_dashboard(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_test_accounts', stdout=StringIO())
        response = self.client.post(
            reverse('test_account_sign_in'), {'account': 'employer'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session['employer_verified_email'],
            'employer@demo.example.invalid',
        )
        person = User.objects.get(email='employer@demo.example.invalid')
        offer = JobOffer.objects.create(
            created_by=person,
            session_key='',
            email=person.email,
            contact={'name': 'Fictional contact', 'email': person.email},
            data=empty_data(),
            source_kind='manual',
            preparation_agreed_at=timezone.now(),
        )
        self.assertContains(
            self.client.get('/accounts/dashboard/'),
            reverse('employer_offer', args=[offer.pk]),
        )
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 200
        )
        with override_settings(CONTINUOUS_SKILLS_ENABLED=False):
            self.assertEqual(
                self.client.get(reverse('employer_offer', args=[offer.pk])).status_code,
                200,
            )

    def test_candidate_suggestions_reject_a_draft_owned_by_another_account(self):
        token = self.candidate()
        session = self.client.session
        draft = session[KEY]
        draft['owner_id'] = -1
        session[KEY] = draft
        session.save()
        self.assertEqual(self.api(token=token).status_code, 403)
