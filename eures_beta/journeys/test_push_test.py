import base64, os, json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from .push_test import subscription


def sample():
    raw = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )
    enc = lambda value: base64.urlsafe_b64encode(value).decode().rstrip('=')
    return {
        'endpoint': 'https://fcm.googleapis.com/fcm/send/fake-test',
        'keys': {'p256dh': enc(raw), 'auth': enc(b'x' * 16)},
    }


@override_settings(DEMO_MODE=True)
@patch.dict(os.environ, {'ME_EMPLOYER_DEV_ACCESS': '1'})
class PushDiagnosticTests(TestCase):
    def test_endpoint_allowlist(self):
        data = sample()
        self.assertEqual(subscription(data), data)
        for url in [
            'https://127.0.0.1/private',
            'http://fcm.googleapis.com/test',
            'https://evil.example/test',
        ]:
            data['endpoint'] = url
            with self.assertRaises(ValueError):
                subscription(data)

    @patch('eures_beta.journeys.push_test.threading.Timer')
    def test_subscribe_send_and_stop(self, timer):
        c = Client()
        self.assertEqual(
            c.post(
                '/api/push-test/send/', data='{}', content_type='application/json'
            ).status_code,
            400,
        )
        self.assertEqual(
            c.post(
                '/api/push-test/subscribe/',
                data=json.dumps(sample()),
                content_type='application/json',
            ).status_code,
            200,
        )
        self.assertEqual(
            c.post(
                '/api/push-test/send/', data='{}', content_type='application/json'
            ).status_code,
            200,
        )
        self.assertEqual(timer.call_args.args[0], 10)
        c.post('/api/push-test/stop/', data='{}', content_type='application/json')
        self.assertEqual(c.get('/api/push-test/status/').json()['state'], 'cancelled')

    def test_csrf_and_loopback(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post('/api/push-test/send/', data='{}', content_type='application/json')
            .status_code,
            403,
        )
        self.assertEqual(
            Client().get('/api/push-test/status/', REMOTE_ADDR='192.0.2.1').status_code,
            404,
        )
