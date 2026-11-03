import hashlib
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone
from eures_beta.employers.models import (
    EmployerEmailLink,
    EmployerCompany,
    EmployerMembership,
)


@patch.dict(
    'os.environ',
    {
        'ME_EMPLOYER_EMAIL_LOCAL': '1',
        'ME_EMPLOYER_DEV_ACCESS': '1',
        'ME_LOCAL_REVIEW_ONLY': '1',
    },
)
class ClosedRegistrationTests(TestCase):
    def test_unknown_email_and_submitted_kind_never_create_user_or_link(self):
        for kind in ('employer', 'adviser'):
            with self.subTest(kind=kind):
                client = Client()
                response = client.post(
                    '/employer/access/',
                    {'email': 'unknown@example.invalid', 'kind': kind},
                )
                self.assertRedirects(response, '/employer/email-sent/')
                self.assertNotIn('employer_test_message', client.session)
        for language, notice in [
            ('fr', 'Les inscriptions publiques sont fermées.'),
            ('en', 'Public registration is closed.'),
            ('de', 'Die öffentliche Registrierung ist geschlossen.'),
        ]:
            self.assertContains(
                self.client.get('/employer/access/?lang=' + language), notice
            )
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(EmployerEmailLink.objects.count(), 0)
        self.assertEqual(EmployerCompany.objects.count(), 0)
        self.assertEqual(EmployerMembership.objects.count(), 0)

    def test_previously_issued_link_cannot_create_a_user(self):
        token = 'fictional-old-connection-token'
        EmployerEmailLink.objects.create(
            email='unknown@example.invalid',
            digest=hashlib.sha256(token.encode()).hexdigest(),
            expires=timezone.now() + timedelta(minutes=15),
        )
        url = '/employer/confirm/' + token + '/'
        self.assertEqual(self.client.get(url).context['stage'], 'invalid')
        self.client.post(url, {'kind': 'employer'})
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_request_is_generic_and_existing_employer_can_still_sign_in(self):
        User = get_user_model()
        user = User.objects.create_user(
            email='existing@example.invalid', kind='employer'
        )
        known, unknown = Client(), Client()
        self.assertEqual(
            known.post('/employer/access/', {'email': user.email}).url,
            unknown.post('/employer/access/', {'email': 'unknown@example.invalid'}).url,
        )
        self.assertEqual(
            known.get('/employer/email-sent/').context['stage'],
            unknown.get('/employer/email-sent/').context['stage'],
        )
        url = known.session['employer_test_message']['link']
        self.assertRedirects(known.post(url), '/employer/connected/')
        self.assertEqual(int(known.session['_auth_user_id']), user.pk)
        self.assertEqual(User.objects.count(), 1)

    def test_adviser_and_inactive_account_cannot_use_employer_login(self):
        for email, kind, active in [
            ('adviser@example.invalid', 'adviser', True),
            ('inactive@example.invalid', 'employer', False),
        ]:
            get_user_model().objects.create_user(
                email=email, kind=kind, is_active=active
            )
            client = Client()
            client.post('/employer/access/', {'email': email})
            self.assertNotIn('employer_test_message', client.session)
        self.assertEqual(EmployerEmailLink.objects.count(), 0)

    def test_account_deleted_after_link_issuance_is_not_recreated(self):
        user = get_user_model().objects.create_user(
            email='deleted@example.invalid', kind='employer'
        )
        self.client.post('/employer/access/', {'email': user.email})
        url = self.client.session['employer_test_message']['link']
        user.delete()
        self.client.post(url)
        self.assertFalse(get_user_model().objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

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
        for kind in ('adviser', 'employer'):
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
