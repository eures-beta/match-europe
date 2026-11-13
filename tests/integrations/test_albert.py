import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings
from eures_beta.integrations.albert import AlbertError, Limits, complete_json


@override_settings(ALBERT_API_KEY='fictional-key', ALBERT_MODEL='fictional-model')
class AlbertClientTests(SimpleTestCase):
    def response(self, opener, content='{"answer": "example"}'):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                'choices': [{'finish_reason': 'stop', 'message': {'content': content}}],
            }
        ).encode()
        opener.return_value.open.return_value.__enter__.return_value = response
        return response

    @patch('eures_beta.integrations.albert.build_opener')
    def test_caller_model_and_budgets_override_defaults_without_losing_transport(
        self, opener
    ):
        response = self.response(opener)
        limits = Limits(
            timeout=25,
            max_elapsed=30,
            response_bytes=20000,
            request_bytes=24000,
            allow_code_fence=False,
        )
        self.assertEqual(
            complete_json([], model='dialogue-model', max_tokens=1800, limits=limits),
            {'answer': 'example'},
        )
        request = opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'dialogue-model')
        self.assertEqual(payload['max_tokens'], 1800)
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertIs(payload['stream'], False)
        self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 25)
        response.read.assert_called_once_with(20001)
        self.assertEqual(request.get_header('Authorization'), 'Bearer fictional-key')

    @patch('eures_beta.integrations.albert.build_opener')
    def test_request_budget_is_checked_before_any_network_call(self, opener):
        with self.assertRaises(AlbertError):
            complete_json(
                [{'role': 'user', 'content': 'x' * 1000}],
                limits=Limits(request_bytes=100),
            )
        opener.assert_not_called()

    @patch('eures_beta.integrations.albert.build_opener')
    def test_response_budget_and_elapsed_deadline_fail_closed(self, opener):
        response = self.response(opener)
        response.read.return_value = b'x' * 101
        with self.assertRaises(AlbertError):
            complete_json([], limits=Limits(response_bytes=100))
        response.read.assert_called_once_with(101)
        self.response(opener)
        with patch(
            'eures_beta.integrations.albert.time.monotonic', side_effect=[10, 41]
        ):
            with self.assertRaises(AlbertError):
                complete_json([], limits=Limits(max_elapsed=30))

    @patch('eures_beta.integrations.albert.build_opener')
    def test_strict_json_callers_do_not_inherit_import_code_fence_tolerance(
        self, opener
    ):
        self.response(opener, '```json\n{"answer": "example"}\n```')
        self.assertEqual(complete_json([]), {'answer': 'example'})
        with self.assertRaises(AlbertError):
            complete_json([], limits=Limits(allow_code_fence=False))

    @patch('eures_beta.integrations.albert.build_opener')
    def test_shared_client_accepts_a_non_employer_schema(self, opener):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                'choices': [
                    {
                        'finish_reason': 'stop',
                        'message': {'content': '{"answer": "example"}'},
                    }
                ]
            }
        ).encode()
        opener.return_value.open.return_value.__enter__.return_value = response
        messages = [{'role': 'user', 'content': 'Fictional generic question'}]
        self.assertEqual(complete_json(messages, max_tokens=100), {'answer': 'example'})
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(json.loads(request.data)['messages'], messages)
        self.assertEqual(json.loads(request.data)['max_tokens'], 100)
        self.assertNotIn('fictional-key', request.data.decode())
        self.assertEqual(request.get_header('Authorization'), 'Bearer fictional-key')

    @patch('eures_beta.integrations.albert.build_opener')
    def test_oversized_truncated_and_invalid_responses_fail_closed(self, opener):
        response = MagicMock()
        opener.return_value.open.return_value.__enter__.return_value = response
        for raw in (
            b'x' * 100001,
            b'not json',
            json.dumps(
                {
                    'choices': [
                        {
                            'finish_reason': 'length',
                            'message': {'content': '{}'},
                        }
                    ]
                }
            ).encode(),
        ):
            with self.subTest(size=len(raw)):
                response.read.return_value = raw
                with self.assertRaises(AlbertError):
                    complete_json([])

    @patch('eures_beta.integrations.albert.build_opener')
    def test_transport_failure_never_exposes_upstream_details(self, opener):
        opener.return_value.open.side_effect = HTTPError(
            'https://example.invalid', 401, 'sensitive detail', {}, None
        )
        with self.assertRaises(AlbertError) as caught:
            complete_json([])
        self.assertEqual(str(caught.exception), 'albert_http_401')

    @override_settings(ALBERT_API_KEY='')
    @patch('eures_beta.integrations.albert.build_opener')
    def test_missing_key_never_opens_a_connection(self, opener):
        with self.assertRaises(AlbertError):
            complete_json([])
        opener.assert_not_called()
