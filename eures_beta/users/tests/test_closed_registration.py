import hashlib
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone
from eures_beta.employers.models import (
    Company,
    CompanyMembership,
)


class ClosedRegistrationTests(TestCase):

    def test_signup_aliases_and_admin_cannot_create_accounts_anonymously(self):
        for url in ('/signup/', '/register/', '/accounts/signup/', '/users/signup/'):
            for method in ('get', 'post'):
                self.assertEqual(
                    getattr(self.client, method)(
                        url, {'email': 'unknown@example.invalid', 'kind': 'employer'}
                    ).status_code,
                    404,
                )
        for method in ('get', 'post'):
            response = getattr(self.client, method)(
                '/admin/users/user/add/',
                {'email': 'unknown@example.invalid', 'kind': 'adviser'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login/', response.url)
        self.assertFalse(get_user_model().objects.exists())

    def test_anonymous_offer_import_does_not_create_an_account(self):
        import json

        response = self.client.post(
            '/api/imports/',
            {
                'kind': 'manual',
                'text': 'Fictional job description',
                'agreement': 'true',
                'email': 'anonymous@example.invalid',
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'anonymous@example.invalid'}
                ),
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.exists())

    def test_ordinary_accounts_cannot_create_users_in_admin(self):
        for kind in ('adviser', 'employer', 'candidate'):
            user = get_user_model().objects.create_user(
                email=kind + '@example.invalid', kind=kind
            )
            client = Client()
            client.force_login(user)
            response = client.post(
                '/admin/users/user/add/',
                {'email': 'new@example.invalid', 'kind': 'employer'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertFalse(
                get_user_model().objects.filter(email='new@example.invalid').exists()
            )
