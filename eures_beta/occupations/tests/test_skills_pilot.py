from itertools import product
from time import time

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer
from eures_beta.occupations.pilot_views import SESSION_KEY, TTL
from eures_beta.occupations.skills_pilot import catalogue
from eures_beta.users.models import User


@override_settings(
    SKILLS_PILOT_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class SkillsPilotTests(TestCase):
    def setUp(self):
        self.cards, self.skills = catalogue()
        self.start = reverse('skills_pilot_start')
        self.url = reverse('skills_pilot_journey', args=['employer'])
        self.candidate_url = reverse('skills_pilot_journey', args=['candidate'])

    def choose(self, occupation='restauration', role='employer'):
        return self.client.post(
            reverse('skills_pilot_journey', args=[role]),
            {'action': 'occupation', 'occupation': occupation},
        )

    def selection(self, role='employer', skill_count=5, behaviour_count=3):
        state = self.client.session[SESSION_KEY][role]
        card = self.cards[state['occupation']]
        return {
            'action': 'selection',
            'occupation': state['occupation'],
            'revision': state['revision'],
            'skills': [item['skillUri'] for item in card['keySkills'][:skill_count]],
            'behaviours': [
                item['skillUri'] for item in card['behaviours'][:behaviour_count]
            ],
            'other': '',
        }

    def test_disabled_outside_explicit_local_loopback(self):
        for change in (
            {'SKILLS_PILOT_ENABLED': False},
            {'DJANGO_ENVIRONMENT': 'production'},
            {'DJANGO_ENVIRONMENT': 'preview'},
            {'EMAIL_DELIVERY_ENABLED': True},
        ):
            with self.subTest(change=change), override_settings(**change):
                self.assertEqual(self.client.get(self.start).status_code, 404)
                self.assertEqual(
                    self.client.post(
                        self.url, {'action': 'occupation', 'occupation': 'restauration'}
                    ).status_code,
                    404,
                )
        for remote in ('192.0.2.1', 'invalid', ''):
            self.assertEqual(
                self.client.get(
                    self.start, REMOTE_ADDR=remote, HTTP_X_FORWARDED_FOR='127.0.0.1'
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.get(self.start, REMOTE_ADDR='::1').status_code, 200
        )

    def test_roles_and_methods(self):
        self.assertEqual(self.client.get('/skills-pilot/admin/').status_code, 404)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.assertEqual(self.client.post(self.start).status_code, 405)

    def test_end_to_end_each_occupation_in_both_roles(self):
        counts = (
            User.objects.count(),
            CandidateProfile.objects.count(),
            JobOffer.objects.count(),
        )
        for role in ('employer', 'candidate'):
            url = reverse('skills_pilot_journey', args=[role])
            for key, lang in product(self.cards, ('fr', 'en', 'de')):
                with self.subTest(role=role, occupation=key, language=lang):
                    self.assertEqual(self.choose(key, role).status_code, 302)
                    response = self.client.get(url, {'step': 'skills', 'lang': lang})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content.count(b'type="checkbox"'), 12)
                    card = self.cards[key]
                    self.assertEqual(
                        list(response.context['form'].fields['skills'].choices),
                        [
                            (
                                item['skillUri'],
                                self.skills[item['skillUri']]['labels'][lang],
                            )
                            for item in card['keySkills']
                        ],
                    )
                    self.assertEqual(
                        response.context['official_occupation_label'],
                        card['occupation']['labels'][lang],
                    )
                    saved = self.client.post(f'{url}?lang={lang}', self.selection(role))
                    self.assertEqual(saved.status_code, 302)
                    review = self.client.get(url, {'step': 'review', 'lang': lang})
                    self.assertEqual(review.status_code, 200)
                    self.assertEqual(len(review.context['selected_skills']), 5)
                    self.assertEqual(len(review.context['selected_behaviours']), 3)
                    self.assertEqual(
                        review.context['selected_skills'],
                        [
                            self.skills[item['skillUri']]['labels'][lang]
                            for item in card['keySkills'][:5]
                        ],
                    )
        self.assertEqual(
            counts,
            (
                User.objects.count(),
                CandidateProfile.objects.count(),
                JobOffer.objects.count(),
            ),
        )

    def test_server_rejects_six_skills_or_four_behaviours_without_saving(self):
        self.choose()
        for count, behaviours in ((6, 3), (5, 4)):
            response = self.client.post(
                self.url, self.selection(skill_count=count, behaviour_count=behaviours)
            )
            self.assertEqual(response.status_code, 400)
            state = self.client.session[SESSION_KEY]['employer']
            self.assertFalse(state['completed'])
            self.assertEqual(state['skills'], [])

    def test_foreign_unknown_and_duplicate_identifiers_rejected(self):
        self.choose()
        for invalid in (
            'made-up-uri',
            self.cards['espaces-verts']['keySkills'][0]['skillUri'],
        ):
            payload = self.selection(skill_count=1)
            payload['skills'] = [invalid]
            self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        payload = self.selection(skill_count=1)
        payload['skills'] *= 2
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        payload = self.selection()
        payload['behaviours'] = ['unknown']
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)

    def test_empty_selection_is_valid_and_not_missing_skills(self):
        self.choose()
        self.assertEqual(
            self.client.post(
                self.url, self.selection(skill_count=0, behaviour_count=0)
            ).status_code,
            302,
        )
        response = self.client.get(self.url, {'step': 'review', 'lang': 'en'})
        self.assertContains(response, 'No selection', count=2)
        self.assertContains(
            response, 'Unselected items are not treated as missing skills.'
        )

    def test_edit_language_switch_keeps_canonical_ids(self):
        self.choose()
        payload = self.selection()
        self.client.post(self.url, payload)
        for language in ('fr', 'en', 'de'):
            response = self.client.get(self.url, {'lang': language, 'step': 'skills'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context['form'].initial['skills'], payload['skills']
            )
            first = payload['skills'][0]
            self.assertContains(response, self.skills[first]['labels'][language])
        updated = self.selection(skill_count=1, behaviour_count=0)
        self.client.post(self.url, updated)
        self.assertEqual(
            self.client.session[SESSION_KEY]['employer']['skills'], updated['skills']
        )

    def test_role_drafts_and_restart_are_independent(self):
        self.choose()
        self.client.post(self.url, self.selection())
        employer = dict(self.client.session[SESSION_KEY]['employer'])
        self.choose('securite', 'candidate')
        self.client.post(self.candidate_url, self.selection('candidate', 2, 1))
        self.assertEqual(self.client.session[SESSION_KEY]['employer'], employer)
        self.client.post(self.candidate_url, {'action': 'restart'})
        self.assertNotIn('candidate', self.client.session[SESSION_KEY])
        self.assertEqual(self.client.session[SESSION_KEY]['employer'], employer)

    def test_changing_occupation_clears_answers_and_rejects_old_tab(self):
        self.choose()
        payload = self.selection()
        self.client.post(self.url, payload)
        stale = self.selection()
        self.choose('espaces-verts')
        state = self.client.session[SESSION_KEY]['employer']
        self.assertEqual(state['skills'], [])
        self.assertEqual(state['behaviours'], [])
        self.assertFalse(state['completed'])
        self.assertEqual(self.client.post(self.url, stale).status_code, 400)
        self.assertEqual(
            self.client.session[SESSION_KEY]['employer']['occupation'], 'espaces-verts'
        )

    def test_stale_revision_rejected(self):
        self.choose()
        payload = self.selection()
        self.client.post(self.url, payload)
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)

    def test_language_change_saves_choices_without_finishing_the_journey(self):
        self.choose()
        payload = self.selection(skill_count=2, behaviour_count=1)
        payload['target_language'] = 'de'
        response = self.client.post(self.url, payload)
        self.assertRedirects(response, self.url + '?lang=de&step=skills')
        state = self.client.session[SESSION_KEY]['employer']
        self.assertEqual(state['skills'], payload['skills'])
        self.assertEqual(state['behaviours'], payload['behaviours'])
        self.assertFalse(state['completed'])

    def test_expired_draft_cannot_be_saved(self):
        self.choose()
        payload = self.selection()
        session = self.client.session
        states = session[SESSION_KEY]
        states['employer']['updated'] = time() - TTL - 1
        session[SESSION_KEY] = states
        session.save()
        self.assertEqual(self.client.post(self.url, payload).status_code, 409)
        self.assertNotIn('employer', self.client.session[SESSION_KEY])
        # A browser may also have dropped its expired session cookie entirely.
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url, payload).status_code, 409)

    def test_no_step_skipping_and_no_cache(self):
        self.assertEqual(self.client.get(self.url, {'step': 'review'}).status_code, 302)
        self.choose()
        self.assertEqual(self.client.get(self.url, {'step': 'review'}).status_code, 302)
        self.assertIn('no-store', self.client.get(self.start)['Cache-Control'])

    def test_csrf_required(self):
        browser = Client(enforce_csrf_checks=True)
        self.assertEqual(
            browser.post(
                self.url, {'action': 'occupation', 'occupation': 'restauration'}
            ).status_code,
            403,
        )

    def test_free_text_is_bounded_and_escaped(self):
        self.choose()
        payload = self.selection()
        payload['other'] = 'x' * 301
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        payload['other'] = '<script>alert("test")</script>'
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        response = self.client.get(self.url, {'step': 'review'})
        self.assertNotContains(response, '<script>alert(')
        self.assertContains(response, '&lt;script&gt;')

    def test_translated_interface(self):
        for lang, title in [
            ('fr', 'Tester le choix des compétences'),
            ('en', 'Try the skills journey'),
            ('de', 'Kompetenzauswahl testen'),
        ]:
            response = self.client.get(self.start, {'lang': lang})
            self.assertContains(response, title)
            self.assertContains(response, f'<html lang="{lang}">')

    def test_unknown_occupation_rejected(self):
        self.assertEqual(self.choose('unknown').status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
