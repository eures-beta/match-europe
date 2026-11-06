from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.candidates import registration
from eures_beta.candidates.journey import KEY, ProjectForm
from eures_beta.candidates.models import CandidateProfile, CandidateRegistration
from eures_beta.candidates.skill_choices import (
    FIELDS,
    VERSION,
    skill_choices,
    skill_groups,
)
from eures_beta.candidates.tests.test_registration import answers
from eures_beta.users.models import User


def project(**changes):
    technical = [uri for uri, label in skill_choices('acquired_skills', 'fr')]
    behaviours = [uri for uri, label in skill_choices('professional_behaviours', 'fr')]
    return {
        'project_mode': 'open',
        'desired_countries': ['FR'],
        'acquired_skills': technical[:1],
        'learning_activities': [],
        'professional_behaviours': behaviours[:3],
        **changes,
    }


@override_settings(EMAIL_DELIVERY_ENABLED=False, DJANGO_ENVIRONMENT='local')
class OpenSkillProjectTests(TestCase):
    def test_all_valid_boundaries_and_canonical_catalogue_version(self):
        technical = [uri for uri, label in skill_choices('acquired_skills', 'fr')]
        for acquired, learning in ((0, 1), (1, 0), (10, 5)):
            for language in ('fr', 'en', 'de'):
                data = project(
                    acquired_skills=technical[:acquired],
                    learning_activities=technical[10 : 10 + learning],
                )
                data['skill_catalogue_version'] = 'untrusted'
                form = ProjectForm(data, language=language)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['skill_catalogue_version'], VERSION)
                self.assertEqual(form.cleaned_data['occupation_references'], [])

    def test_invalid_counts_ids_duplicates_and_overlap_are_rejected(self):
        technical = [uri for uri, label in skill_choices('acquired_skills', 'fr')]
        behaviours = [
            uri for uri, label in skill_choices('professional_behaviours', 'fr')
        ]
        for change, field in (
            ({'acquired_skills': [], 'learning_activities': []}, 'acquired_skills'),
            ({'acquired_skills': technical[:11]}, 'acquired_skills'),
            ({'learning_activities': technical[10:16]}, 'learning_activities'),
            ({'professional_behaviours': []}, 'professional_behaviours'),
            ({'professional_behaviours': behaviours[:2]}, 'professional_behaviours'),
            ({'professional_behaviours': behaviours[:4]}, 'professional_behaviours'),
            ({'acquired_skills': [technical[0]] * 2}, 'acquired_skills'),
            (
                {'professional_behaviours': [behaviours[0]] * 3},
                'professional_behaviours',
            ),
            ({'learning_activities': technical[:1]}, 'learning_activities'),
            ({'project_mode': 'unknown'}, 'project_mode'),
            *[({name: ['http://attacker.invalid/fake']}, name) for name in FIELDS],
            ({'professional_behaviours': technical[:3]}, 'professional_behaviours'),
        ):
            with self.subTest(change=change):
                form = ProjectForm(project(**change))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_occupation_mode_preserves_existing_rules_and_clears_skill_answers(self):
        data = project(project_mode='occupation', desired_occupations='Fictional job')
        form = ProjectForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        for name in FIELDS:
            self.assertEqual(form.cleaned_data[name], [])
        self.assertEqual(form.cleaned_data['skill_catalogue_version'], '')
        self.assertFalse(ProjectForm({'desired_countries': ['FR']}).is_valid())
        form = ProjectForm(
            {'desired_countries': ['FR'], 'desired_occupations': 'Legacy job'}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['project_mode'], 'occupation')

    def test_open_mode_clears_occupation_and_uses_only_official_trilingual_concepts(
        self,
    ):
        form = ProjectForm(
            project(desired_occupations='Old job', occupation_references=['rome:D1102'])
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['desired_occupations'], '')
        self.assertEqual(form.cleaned_data['occupation_references'], [])
        groups, skills = skill_groups()
        self.assertFalse(
            set(groups['acquired_skills']) & set(groups['professional_behaviours'])
        )
        for group in groups.values():
            for uri in group:
                self.assertEqual(skills[uri]['skillType'], 'skill/competence')
                for language in ('fr', 'en', 'de'):
                    self.assertTrue(skills[uri]['labels'][language])

    def test_registration_confirmation_profile_and_edit_round_trip_in_three_languages(
        self,
    ):
        for language in ('fr', 'en', 'de'):
            data = answers()
            data.update(project())
            pending = registration.create_request(
                f'candidate-{language}@example.invalid', data, language
            )
            self.assertEqual(User.objects.count(), CandidateProfile.objects.count())
            self.assertEqual(
                pending.answers['acquired_skills'], data['acquired_skills']
            )
            user = registration.confirm_registration(registration.token_for(pending))
            profile = user.candidate_profile
            self.assertEqual(profile.project_mode, 'open')
            self.assertEqual(profile.skill_catalogue_version, VERSION)
            self.assertEqual(
                profile.professional_behaviours, data['professional_behaviours']
            )
            self.client.force_login(user)
            for display_language in ('fr', 'en', 'de'):
                response = self.client.get(
                    reverse('candidate_profile'),
                    {'lang': display_language},
                    secure=True,
                )
                labels = dict(skill_choices('acquired_skills', display_language))
                self.assertContains(response, labels[data['acquired_skills'][0]])
                self.assertNotContains(response, data['acquired_skills'][0])
            self.client.post(reverse('candidate_profile_edit'), secure=True)
            draft = self.client.session[KEY]
            self.assertEqual(
                draft['data']['professional_behaviours'],
                data['professional_behaviours'],
            )
            changed = dict(
                data, acquired_skills=[], learning_activities=data['acquired_skills']
            )
            registration.update_profile(user, changed, language)
            profile.refresh_from_db()
            self.assertEqual(profile.acquired_skills, [])
            self.assertEqual(profile.learning_activities, data['acquired_skills'])
            profile.professional_behaviours = []
            with self.assertRaises(ValidationError):
                profile.save()
        self.assertEqual(CandidateRegistration.objects.count(), 0)

    def test_pending_answers_are_revalidated_before_account_creation(self):
        data = answers()
        data.update(project())
        pending = registration.create_request('tampered@example.invalid', data, 'fr')
        pending.answers['professional_behaviours'] = []
        pending.save()
        with self.assertRaises(ValidationError):
            registration.confirm_registration(registration.token_for(pending))
        self.assertEqual(User.objects.count(), 0)
        self.assertTrue(CandidateRegistration.objects.filter(pk=pending.pk).exists())

    def test_journey_post_review_language_switch_and_server_errors(self):
        self.client.get('/candidate/prepare/?lang=fr', secure=True)
        token = self.client.session[KEY]['token']
        partial = project(
            professional_behaviours=project()['professional_behaviours'][:2]
        )
        response = self.client.post(
            '/candidate/prepare/?step=1&lang=fr',
            {**partial, 'token': token, 'target_language': 'de'},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[KEY]['unlocked'], 1)
        self.assertEqual(
            self.client.session[KEY]['data']['professional_behaviours'],
            partial['professional_behaviours'],
        )
        response = self.client.get(response.url, secure=True)
        self.assertContains(response, 'data-skill-section', count=3)
        self.assertContains(response, 'checked')
        response = self.client.post(
            '/candidate/prepare/?step=1&lang=fr',
            {**partial, 'token': token, 'action': 'continue'},
            secure=True,
        )
        self.assertEqual(self.client.session[KEY]['unlocked'], 1)
        self.assertTrue(response.context['error_summary'])
        response = self.client.post(
            '/candidate/prepare/?step=1&lang=fr',
            {**project(), 'token': token, 'action': 'continue'},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[KEY]['unlocked'], 2)
        # Full questionnaire continues to the usual review and verified signup.
        self.client.post(
            '/candidate/prepare/?step=2&lang=fr',
            {'token': token, 'action': 'continue', 'mobility': 'discuss'},
            secure=True,
        )
        data = answers()
        self.client.post(
            '/candidate/prepare/?step=3&lang=fr',
            {**data, 'token': token, 'action': 'continue'},
            secure=True,
        )
        review = self.client.get('/candidate/prepare/?step=4&lang=de', secure=True)
        label = dict(skill_choices('acquired_skills', 'de'))[
            project()['acquired_skills'][0]
        ]
        self.assertContains(review, label)
        self.assertNotContains(review, project()['acquired_skills'][0])
        response = self.client.post(
            '/candidate/prepare/?step=4&lang=de',
            {
                'token': token,
                'action': 'finish',
                'display_name': 'Fictional candidate',
                'contact_email': 'journey-open@example.invalid',
                'reviewed': 'on',
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 0)
        pending = CandidateRegistration.objects.get()
        self.client.get(
            reverse('candidate_registration_confirm'),
            {'token': registration.token_for(pending)},
            secure=True,
        )
        self.client.post(reverse('candidate_registration_confirm'), secure=True)
        profile = CandidateProfile.objects.get()
        self.assertEqual(profile.acquired_skills, project()['acquired_skills'])
        self.assertEqual(
            profile.professional_behaviours, project()['professional_behaviours']
        )
        self.assertEqual(profile.project_mode, 'open')

    def test_partial_language_save_relocks_previously_completed_project(self):
        self.client.get('/candidate/prepare/?lang=fr', secure=True)
        session = self.client.session
        draft = session[KEY]
        draft['unlocked'] = 4
        session[KEY] = draft
        session.save()
        response = self.client.post(
            '/candidate/prepare/?step=1&lang=fr',
            {
                **project(professional_behaviours=[]),
                'token': draft['token'],
                'target_language': 'en',
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[KEY]['unlocked'], 1)
        response = self.client.get('/candidate/prepare/?step=4&lang=en', secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=1', response.url)
        self.assertEqual(CandidateRegistration.objects.count(), 0)

    def test_csrf_and_private_profile_access_remain_enforced(self):
        browser = Client(enforce_csrf_checks=True)
        browser.get('/candidate/prepare/', secure=True)
        self.assertEqual(
            browser.post('/candidate/prepare/', project(), secure=True).status_code, 403
        )
        self.assertEqual(
            browser.get(reverse('candidate_profile'), secure=True).status_code, 302
        )
        employer = User.objects.create_user('employer@example.invalid', kind='employer')
        self.client.force_login(employer)
        self.assertEqual(
            self.client.get(reverse('candidate_profile'), secure=True).status_code, 403
        )
