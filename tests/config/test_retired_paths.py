"""Removed prototype routes cannot be enabled by obsolete environment variables."""

from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client


class RetiredPathsTests(TestCase):
    def test_previous_authenticated_retired_session_cannot_open_dashboard(self):
        user = get_user_model().objects.create_user(
            kind='adviser', email="candidate@example.invalid"
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get("/dashboard/").status_code, 404)

    def test_previous_draft_session_cannot_open_profile(self):
        user = get_user_model().objects.create_user(
            kind='adviser', email="draft@example.invalid"
        )
        session = self.client.session
        session["draft_user"] = user.pk
        session.save()
        self.assertEqual(self.client.get("/profile/").status_code, 404)

    def test_django_admin_authentication_remains_available(self):
        self.assertRedirects(
            self.client.get("/admin/"),
            "/admin/login/?next=/admin/",
            fetch_redirect_response=False,
        )
        user = get_user_model().objects.create_superuser(
            kind='adviser',
            email="operator@example.invalid",
            password="fictional-test-password",
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_root_remains_available_without_retired_or_fictional_accounts(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertTemplateUsed(self.client.get("/"), "home.html")
        self.assertFalse(get_user_model().objects.exists())

    def test_retired_login_links_and_import_endpoints_are_unavailable(self):
        for path in ("/access/", "/confirm/fictional/"):
            for method in (self.client.get, self.client.post):
                with self.subTest(path=path, method=method.__name__):
                    self.assertEqual(method(path).status_code, 404)

    def test_legacy_seed_command_is_no_longer_available(self):
        from django.core.management import get_commands

        self.assertNotIn('seed_retired', get_commands())

    def test_retired_routes_are_absent_even_with_old_flags_and_employer_session(self):
        employer = get_user_model().objects.create_user(
            kind='employer', email='retired@example.invalid'
        )
        self.client.force_login(employer)
        paths = (
            '/employer/access/',
            '/employer/email-sent/',
            '/employer/test-inbox/',
            '/employer/confirm/fictional/',
            '/employer/logout/',
            '/employer/pages/push-test.html',
            '/employer/pages/push-test-sw.js',
            '/api/push-test/config/',
            '/api/push-test/send/',
            '/employer/offers/00000000-0000-0000-0000-000000000001/search/',
            '/employer/offers/00000000-0000-0000-0000-000000000001/search/check/',
        )
        with patch.dict(
            'os.environ',
            {
                'ME_DEMO_MODE': '1',
                'ME_SHARED_DEMO': '1',
                'ME_EMPLOYER_DEV_ACCESS': '1',
                'ME_EMPLOYER_EMAIL_LOCAL': '1',
                'ME_LOCAL_REVIEW_ONLY': '1',
            },
        ):
            for path in paths:
                for client in (self.client, Client()):
                    for method in (client.get, client.post):
                        with self.subTest(path=path, method=method.__name__):
                            self.assertEqual(method(path, secure=True).status_code, 404)

    def test_employer_workspace_and_import_keep_account_and_csrf_guards(self):
        self.assertEqual(self.client.get('/employer/offers/').status_code, 302)
        self.assertEqual(self.client.get('/api/job-offers/').status_code, 403)
        client = Client(enforce_csrf_checks=True)
        employer = get_user_model().objects.create_user(
            kind='employer', email='csrf@example.invalid'
        )
        client.force_login(employer)
        self.assertEqual(client.post('/api/job-offers/', {}).status_code, 403)
