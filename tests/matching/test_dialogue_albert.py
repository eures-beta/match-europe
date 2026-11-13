import json
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.test import override_settings, TestCase
from django.urls import reverse
from django.core.management import call_command, CommandError

from eures_beta.matching import dialogue_albert as adapter
from eures_beta.matching import dialogue_services as dialogue
from . import test_dialogue


@override_settings(
    **{
        **test_dialogue.SETTINGS,
        'ALBERT_SIMULATED': False,
        'ALBERT_API_KEY': 'fictional-test-key',
        'ALBERT_DIALOGUE_MODEL': 'fictional-model',
    }
)
class AlbertAdapterTests(TestCase):
    # Inherit fixture setup only; the simulator tests remain on their own class.
    setUpTestData = classmethod(test_dialogue.DialogueTests.setUpTestData.__func__)
    setUp = test_dialogue.DialogueTests.setUp
    data = test_dialogue.DialogueTests.data

    def test_real_evaluation_is_explicit_and_bounded(self):
        with patch.object(adapter, 'ask') as ask:
            with self.assertRaises(CommandError):
                call_command('evaluate_dialogue_albert')
            ask.assert_not_called()
        clarification = dict(
            reply='Quelle portée ?',
            outcome='clarify',
            scope='unknown',
            changes={},
            evidence={},
        )
        with patch.object(
            adapter, 'ask', side_effect=[clarification, self.model()] * 3
        ) as ask:
            call_command('evaluate_dialogue_albert', live=True)
            self.assertEqual(ask.call_count, 6)

    def test_real_evaluation_stops_on_first_invalid_result(self):
        with patch.object(adapter, 'ask', side_effect=adapter.Unavailable) as ask:
            with self.assertRaises(CommandError):
                call_command('evaluate_dialogue_albert', live=True)
            self.assertEqual(ask.call_count, 1)

    def model(self, **kw):
        return dict(
            reply='Vous acceptez sous conditions pour cette offre.',
            outcome='conditional',
            scope='offer',
            changes={},
            evidence={},
            **kw,
        )

    def propose_live(self, model, text='Je peux venir un samedi sur deux.', **extra):
        with patch.object(adapter, 'ask', return_value=model) as ask:
            page = self.client.post(
                self.url, {'action': 'reply', **self.data(text, 'offer'), **extra}
            )
        return page, ask

    def test_live_two_turn_dialogue_proposal_then_explicit_acceptance(self):
        clarify = dict(
            reply='Cette disponibilité concerne-t-elle cette offre uniquement ?',
            outcome='clarify',
            scope='unknown',
            changes={},
            evidence={},
        )
        page, ask = self.propose_live(clarify)
        self.assertEqual(page.status_code, 200)
        self.assertFalse(self.obj.answers.exists())
        token = page.context['form']['history_token'].value()
        page, ask = self.propose_live(
            self.model(), 'Oui, pour cette offre uniquement.', history_token=token
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(ask.call_args.args[-1]), 3)
        self.assertTrue(ask.call_args.args[0]['question'])
        proposal = page.context['proposal']
        with patch.object(adapter, 'ask') as ask:
            accepted = self.client.post(
                self.url, dict(action='accept', token=proposal['token'])
            )
            self.assertEqual(accepted.status_code, 302)
            ask.assert_not_called()
        self.assertEqual(self.obj.answers.get().value, 'conditional')
        answer = self.obj.answers.get()
        self.assertIn('samedi sur deux', answer.detail)
        self.assertEqual(
            [turn['role'] for turn in answer.dialogue['turns']],
            [
                'candidate',
                'assistant',
                'candidate',
            ],
        )
        self.assertContains(self.client.get(self.url), clarify['reply'])
        self.assertFalse(self.obj.agreements.exists())

    def test_http_payload_is_minimal_and_bounded(self):
        body = {
            'choices': [
                {
                    'finish_reason': 'stop',
                    'message': {'content': json.dumps(self.model())},
                }
            ]
        }
        response = BytesIO(json.dumps(body).encode())
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response
        with patch('eures_beta.integrations.albert.build_opener', return_value=opener):
            result = adapter.ask(self.row, 'Un samedi sur deux.', 'offer', 'fr', [])
        self.assertEqual(result['outcome'], 'conditional')
        request = opener.open.call_args.args[0]
        payload = json.loads(request.data)
        supplied = json.loads(payload['messages'][1]['content'])
        self.assertNotIn('email', request.data.decode())
        self.assertNotIn(self.user.email, request.data.decode())
        self.assertNotIn(self.pair.candidate.display_name, request.data.decode())
        self.assertEqual(supplied['declared'], self.row['presented']['declared'])
        self.assertEqual(
            request.full_url, 'https://albert.api.etalab.gouv.fr/v1/chat/completions'
        )
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 25)
        self.assertEqual(payload['model'], 'fictional-model')
        self.assertEqual(payload['max_tokens'], 1800)
        self.assertEqual(payload['stream'], False)

    def test_invalid_model_content_is_rejected(self):
        cases = [
            {**self.model(), 'outcome': 'send'},
            {**self.model(), 'reply': '<script>alert(1)</script>'},
            {**self.model(), 'reply': 'Go to https://example.invalid'},
            {**self.model(), 'changes': {'user': 1}, 'evidence': {'user': 'Un samedi'}},
            dict(
                reply='Changement',
                outcome='changed',
                scope='profile',
                changes={'schedule_saturday': ['wrong']},
                evidence={'schedule_saturday': 'Un samedi'},
            ),
            dict(
                reply='Changement',
                outcome='changed',
                scope='profile',
                changes={'schedule_saturday': []},
                evidence={'schedule_saturday': 'Invented quote'},
            ),
            {**self.model(), 'extra': True},
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(adapter.Unavailable):
                    adapter.validate(value, self.row, 'Un samedi sur deux.', 'offer')

    def test_evidenced_general_change_requires_separate_review(self):
        source = 'Je ne peux plus travailler le samedi.'
        model = dict(
            reply='Vous souhaitez retirer le samedi de vos disponibilités générales.',
            outcome='changed',
            scope='profile',
            changes={'schedule_saturday': []},
            evidence={'schedule_saturday': source},
        )
        adapter.validate(model, self.row, source, 'profile')
        with patch.object(adapter, 'ask', return_value=model):
            page = self.client.post(
                self.url, {'action': 'reply', **self.data(source, 'profile')}
            )
        token = page.context['proposal']['token']
        response = self.client.post(
            self.url, dict(action='accept', token=token, update_profile='on')
        )
        self.assertEqual(response.status_code, 302)
        self.pair.candidate.refresh_from_db()
        self.assertEqual(self.pair.candidate.schedule_saturday, ['morning'])

    def test_unavailable_and_quota_fall_back_without_write(self):
        with patch.object(adapter, 'ask', side_effect=adapter.Unavailable):
            for i in range(7):
                page = self.client.post(self.url, {'action': 'reply', **self.data()})
                self.assertEqual(page.status_code, 503)
                self.assertContains(page, 'form', status_code=503)
        self.assertFalse(self.obj.answers.exists())
        with patch.object(adapter, 'ask') as ask:
            self.client.post(self.url, {'action': 'reply', **self.data()})
            ask.assert_not_called()

    def test_albert_dialogue_calls_in_every_environment_without_implicit_simulation(
        self,
    ):
        body = {
            'choices': [
                {
                    'finish_reason': 'stop',
                    'message': {'content': json.dumps(self.model())},
                }
            ]
        }
        for environment in ('local', 'preview', 'production'):
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value = BytesIO(
                json.dumps(body).encode()
            )
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment, EMAIL_DELIVERY_ENABLED=True
                ),
                patch(
                    'eures_beta.integrations.albert.build_opener', return_value=opener
                ),
            ):
                result = adapter.ask(self.row, 'oui', '', 'fr', [])
                self.assertEqual(result['outcome'], 'conditional')
                opener.open.assert_called_once()
                self.assertEqual(
                    self.client.get(self.url, REMOTE_ADDR='192.0.2.1').status_code, 200
                )

    def test_network_errors_and_truncated_response_are_closed(self):
        for raw in [
            b'bad json',
            json.dumps({'choices': [{'finish_reason': 'length'}]}).encode(),
            b'x' * 20001,
        ]:
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value = BytesIO(raw)
            with patch(
                'eures_beta.integrations.albert.build_opener', return_value=opener
            ):
                with self.assertRaises(adapter.Unavailable):
                    adapter.ask(self.row, 'oui', '', 'fr', [])
        with patch('eures_beta.integrations.albert.build_opener', side_effect=OSError):
            with self.assertRaises(adapter.Unavailable):
                adapter.ask(self.row, 'oui', '', 'fr', [])
