import logging

from django.test import SimpleTestCase

from eures_beta.logging import RedactAccessLinks


class AccessLogTests(SimpleTestCase):
    def test_confirmation_and_invitation_tokens_are_redacted_after_interpolation(self):
        record = logging.LogRecord(
            'django.server',
            logging.INFO,
            __file__,
            1,
            'GET %s HTTP/1.1',
            ('/confirm/private-token/?invite=private-invitation&lang=en',),
            None,
        )
        self.assertTrue(RedactAccessLinks().filter(record))
        self.assertEqual(
            record.getMessage(),
            'GET /confirm/[redacted]/?invite=[redacted]&lang=en HTTP/1.1',
        )

    def test_regular_messages_remain_readable(self):
        record = logging.LogRecord(
            'django.request',
            logging.WARNING,
            __file__,
            1,
            'Not Found: %s',
            ('/missing/',),
            None,
        )
        RedactAccessLinks().filter(record)
        self.assertEqual(record.getMessage(), 'Not Found: /missing/')
