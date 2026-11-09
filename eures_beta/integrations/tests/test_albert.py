import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings
from eures_beta.integrations.albert import AlbertError, complete_json


@override_settings(ALBERT_API_KEY='fictional-key', ALBERT_MODEL='fictional-model')
class AlbertClientTests(SimpleTestCase):
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
