"""Frozen signed-token contract for invitation migration fixtures."""

from django.core import signing


def assert_token_preserved(test, token, invitation):
    test.assertEqual(
        signing.loads(token, salt='users.employer-invitation.v1'),
        {'id': str(invitation.pk), 'nonce': str(invitation.nonce)},
    )
