from datetime import timedelta
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
import zipfile

from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer
from eures_beta.users.models import User
from eures_beta.occupations import albert_skills as service
from eures_beta.occupations.catalog import occupation_index
from eures_beta.occupations.models import OccupationSkillSuggestion as Suggestion
from eures_beta.occupations.pilot_views import SESSION_KEY
from eures_beta.occupations.skill_source import load_source
from eures_beta.occupations.skills_pilot import catalogue


@override_settings(
    SKILLS_PILOT_ENABLED=True,
    SKILLS_ALBERT_ENABLED=True,
    SKILLS_ALBERT_SIMULATED=False,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_API_KEY='fictional-secret',
)
class SuggestionTests(TestCase):
    def setUp(self):
        cards, skills = catalogue()
        covered = {card['occupation']['uri'] for card in cards.values()}
        self.uri = next(uri for uri in occupation_index() if uri not in covered)
        self.skills = dict(list(skills.items())[:10])
        self.linked = {uri: 'essential' for uri in self.skills}
        self.values = list(self.skills)[:8]
        self.source_patch = patch.object(
            service, 'source_for', return_value=(self.skills, self.linked)
        )
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)
        self.ask_patch = patch.object(service, 'ask', return_value=self.values)
        self.ask = self.ask_patch.start()
        self.addCleanup(self.ask_patch.stop)
        self.url = reverse('skills_pilot_journey', args=['employer'])
        self.users = {
            role: User.objects.create_user(role + '@albert-fixture.invalid', kind=role)
            for role in ('employer', 'candidate')
        }
        self.client.force_login(self.users['employer'])

    def post(self, role='employer', **extra):
        self.client.force_login(self.users[role])
        return self.client.post(
            reverse('skills_pilot_journey', args=[role]),
            {'action': 'resolve', 'occupation': self.uri, **extra},
        )

    def test_shared_persistent_cache_revalidated_without_second_call(self):
        first = service.resolve(self.uri, generate=True)
        self.assertEqual(first['keySkills'][0]['skillUri'], self.values[0])
        self.assertEqual(Suggestion.objects.get().skill_uris, self.values)
        self.assertEqual(service.resolve(self.uri, generate=True), first)
        self.assertEqual(service.resolve(self.uri), first)
        self.ask.assert_called_once()
        # A cached URI no longer in the verified source cannot be reused.
        self.linked.pop(self.values[0])
        with self.assertRaises(service.SuggestionUnavailable):
            service.resolve(self.uri)

    def test_unknown_duplicate_empty_and_foreign_uris_never_become_ready(self):
        for result in (
            [],
            ['invented'],
            self.values * 2,
            [self.values[0]] * 2,
            {},
            [None],
        ):
            Suggestion.objects.all().delete()
            self.ask.return_value = result
            with self.assertRaises(service.SuggestionUnavailable):
                service.resolve(self.uri, generate=True)
            self.assertFalse(Suggestion.objects.filter(status='ready').exists())

    def test_failure_cooldown_pending_and_expired_lease(self):
        self.ask.side_effect = service.SuggestionUnavailable()
        with self.assertRaises(service.SuggestionUnavailable):
            service.resolve(self.uri, generate=True)
        self.assertEqual(Suggestion.objects.get().status, 'failed')
        self.ask.reset_mock(side_effect=True)
        self.ask.return_value = self.values
        with self.assertRaises(service.SuggestionUnavailable):
            service.resolve(self.uri, generate=True)
        self.ask.assert_not_called()
        Suggestion.objects.update(
            status='pending', updated_at=timezone.now() - timedelta(seconds=61)
        )
        service.resolve(self.uri, generate=True)
        self.assertEqual(Suggestion.objects.get().status, 'ready')

    def test_model_and_simulation_have_distinct_cache_keys(self):
        service.resolve(self.uri, generate=True)
        with override_settings(SKILLS_ALBERT_SIMULATED=True):
            service.resolve(self.uri, generate=True)
        with override_settings(ALBERT_MODEL='another-model'):
            service.resolve(self.uri, generate=True)
        self.assertEqual(Suggestion.objects.count(), 3)

    def test_disabled_csrf_and_get_never_call(self):
        for changes in (
            {'SKILLS_ALBERT_ENABLED': False},
            {'SKILLS_PILOT_ENABLED': False, 'CONTINUOUS_SKILLS_ENABLED': False},
        ):
            with override_settings(**changes):
                self.assertIn(self.post().status_code, (400, 404))
                with self.assertRaises(service.SuggestionUnavailable):
                    service.resolve(self.uri, generate=True)
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(self.url, {'action': 'resolve', 'occupation': self.uri})
            .status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                self.url, {'action': 'resolve', 'occupation': self.uri}
            ).status_code,
            200,
        )
        self.ask.assert_not_called()
        self.assertFalse(Suggestion.objects.exists())

    def test_anonymous_and_wrong_role_cannot_generate(self):
        for user in (None, self.users['candidate']):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(
                self.client.post(
                    self.url,
                    {'action': 'resolve', 'occupation': self.uri},
                    REMOTE_ADDR='192.0.2.1',
                ).status_code,
                403,
            )
        self.ask.assert_not_called()

    def test_remote_generation_in_every_environment_with_emails_enabled(self):
        for environment in ('local', 'preview', 'production'):
            Suggestion.objects.all().delete()
            self.ask.reset_mock()
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment, EMAIL_DELIVERY_ENABLED=True
                ),
            ):
                response = self.client.post(
                    self.url,
                    {'action': 'resolve', 'occupation': self.uri},
                    REMOTE_ADDR='192.0.2.1',
                )
                self.assertEqual(response.status_code, 302)
                self.ask.assert_called_once()
                self.assertEqual(Suggestion.objects.get().status, 'ready')

    def test_both_roles_trilingual_selection_review_and_reuse_without_business_writes(
        self,
    ):
        counts = (
            User.objects.count(),
            CandidateProfile.objects.count(),
            JobOffer.objects.count(),
        )
        for role in ('employer', 'candidate'):
            self.assertEqual(self.post(role).status_code, 302)
            url = reverse('skills_pilot_journey', args=[role])
            for language in ('fr', 'en', 'de'):
                page = self.client.get(url, {'lang': language, 'step': 'skills'})
                self.assertContains(
                    page, self.skills[self.values[0]]['labels'][language]
                )
                self.assertNotContains(page, 'fictional-secret')
                self.assertEqual(
                    len(page.context['form'].fields['behaviours'].choices), 0
                )
            state = self.client.session[SESSION_KEY][role]
            payload = {
                'action': 'selection',
                'occupation': self.uri,
                'revision': state['revision'],
                'skills': self.values[:2],
            }
            self.assertEqual(self.client.post(url, payload).status_code, 302)
            page = self.client.get(url, {'step': 'review'})
            self.assertEqual(len(page.context['selected_skills']), 2)
            payload['revision'] = self.client.session[SESSION_KEY][role]['revision']
            payload['skills'] = ['invented']
            self.assertEqual(self.client.post(url, payload).status_code, 400)
        self.ask.assert_called_once()
        self.assertEqual(
            counts,
            (
                User.objects.count(),
                CandidateProfile.objects.count(),
                JobOffer.objects.count(),
            ),
        )

    def test_failure_preserves_previous_journey_and_offers_retry(self):
        self.client.post(
            self.url, {'action': 'occupation', 'occupation': 'restauration'}
        )
        previous = dict(self.client.session[SESSION_KEY]['employer'])
        self.ask.side_effect = service.SuggestionUnavailable()
        response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(previous, self.client.session[SESSION_KEY]['employer'])
        self.assertTrue(response.context['pilot_error'])

    def test_unverified_occupation_and_missing_source_never_call_model(self):
        with patch.object(service, 'source_for', side_effect=ValueError()):
            self.assertEqual(self.post(occupation='unknown').status_code, 400)
        self.ask.assert_not_called()

    def test_waiting_and_failure_messages_translated_and_search_does_not_generate(self):
        for lang, phrase in [
            (
                'fr',
                'Un instant, nous recherchons les compétences associées à ce métier afin de vous les proposer',
            ),
            ('en', 'One moment, we are looking'),
            ('de', 'Einen Moment'),
        ]:
            with patch(
                'eures_beta.occupations.pilot_views.suggestions',
                return_value=[{'uri': self.uri, 'label': 'Fictional <occupation>'}],
            ):
                page = self.client.get(self.url, {'q': 'test', 'lang': lang})
            self.assertContains(page, phrase)
            self.assertContains(page, 'Fictional &lt;occupation&gt;')
            self.assertContains(page, 'role="status"')
        self.ask.assert_not_called()


@override_settings(
    SKILLS_ALBERT_SIMULATED=False,
    ALBERT_API_KEY='fictional-key',
    ALBERT_MODEL='fixture-model',
)
class TransportTests(SimpleTestCase):
    @patch('eures_beta.occupations.albert_skills.build_opener')
    def test_bounded_request_no_redirect_and_verified_output(self, opener):
        uri = next(iter(occupation_index()))
        skills = {'verified': {'labels': {'fr': 'Compétence fictive'}}}
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                'choices': [
                    {
                        'finish_reason': 'stop',
                        'message': {'content': '{"skills": ["verified"]}'},
                    }
                ]
            }
        ).encode()
        opener.return_value.open.return_value.__enter__.return_value = response
        self.assertEqual(
            service.ask(uri, skills, {'verified': 'essential'}), ['verified']
        )
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(
            request.full_url, 'https://albert.api.etalab.gouv.fr/v1/chat/completions'
        )
        self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 35)
        self.assertEqual(response.read.call_args.args, (30001,))
        self.assertNotIn('fictional-key', request.data.decode())
        for raw in (
            b'x' * 30001,
            b'{}',
            json.dumps({'choices': [{'finish_reason': 'length'}]}).encode(),
        ):
            response.read.return_value = raw
            with self.assertRaises(service.SuggestionUnavailable):
                service.ask(uri, skills, {'verified': 'essential'})
        opener.return_value.open.side_effect = TimeoutError()
        with self.assertRaises(service.SuggestionUnavailable):
            service.ask(uri, skills, {'verified': 'essential'})

    @override_settings(SKILLS_ALBERT_SIMULATED=True)
    @patch('eures_beta.occupations.albert_skills.build_opener')
    def test_simulation_never_opens_network(self, opener):
        self.assertEqual(
            service.ask('unused', {}, {'verified': 'essential'}), ['verified']
        )
        opener.assert_not_called()

    def test_source_checksum_and_trilingual_relations_are_checked(self):
        with TemporaryDirectory() as directory:
            pinned = {}
            for lang in ('fr', 'en', 'de'):
                path = Path(directory) / f'esco-1.2.1-{lang}.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr(
                        f'skills_{lang}.csv',
                        'conceptUri,preferredLabel\nskill,Official ' + lang + '\n',
                    )
                    archive.writestr(
                        f'occupationSkillRelations_{lang}.csv',
                        'occupationUri,skillUri,relationType\noccupation,skill,essential\n',
                    )
                pinned[lang] = hashlib.sha256(path.read_bytes()).hexdigest()
            with patch('eures_beta.occupations.skill_source.PINNED', pinned):
                skills, relations = load_source(directory)
                self.assertEqual(skills['skill']['labels']['de'], 'Official de')
                self.assertEqual(relations['occupation']['skill'], 'essential')
                load_source.cache_clear()
                (Path(directory) / 'esco-1.2.1-fr.zip').write_bytes(b'corrupted')
                with self.assertRaises(ValueError):
                    load_source(directory)
            load_source.cache_clear()
