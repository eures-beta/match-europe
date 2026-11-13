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
from eures_beta.skills import albert_skills as service
from eures_beta.occupations.catalog import occupation_index
from eures_beta.skills.models import OccupationSkillSuggestion as Suggestion
from eures_beta.skills.skill_source import load_source
from eures_beta.skills.skills_pilot import catalogue


@override_settings(
    ALBERT_SIMULATED=False,
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
        self.users = {
            role: User.objects.create_user(role + '@albert-fixture.invalid', kind=role)
            for role in ('employer', 'candidate')
        }
        self.client.force_login(self.users['employer'])

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
        with override_settings(ALBERT_SIMULATED=True):
            service.resolve(self.uri, generate=True)
        with override_settings(ALBERT_MODEL='another-model'):
            service.resolve(self.uri, generate=True)
        self.assertEqual(Suggestion.objects.count(), 3)


@override_settings(
    ALBERT_SIMULATED=False,
    ALBERT_API_KEY='fictional-key',
    ALBERT_MODEL='fixture-model',
)
class TransportTests(SimpleTestCase):
    @patch('eures_beta.integrations.albert.build_opener')
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
        self.assertEqual(json.loads(request.data)['model'], 'fixture-model')
        self.assertEqual(json.loads(request.data)['max_tokens'], 2000)
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

    @override_settings(ALBERT_SIMULATED=True)
    @patch('eures_beta.integrations.albert.build_opener')
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
            with patch('eures_beta.skills.skill_source.PINNED', pinned):
                skills, relations = load_source(directory)
                self.assertEqual(skills['skill']['labels']['de'], 'Official de')
                self.assertEqual(relations['occupation']['skill'], 'essential')
                load_source.cache_clear()
                (Path(directory) / 'esco-1.2.1-fr.zip').write_bytes(b'corrupted')
                with self.assertRaises(ValueError):
                    load_source(directory)
            load_source.cache_clear()
