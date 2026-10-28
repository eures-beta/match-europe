"""The deployed settings must opt into demonstrations, never force them."""

import json
import os
import subprocess
import sys
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from config.demo import ensure_demo
from eures_beta.candidates.models import Candidate
from eures_beta.accounts.models import Profile


class DemoSettingsTests(SimpleTestCase):
    def mode(self, **values):
        environment = os.environ.copy()
        for name in ("ME_DEMO_MODE", "ME_SHARED_DEMO", "DJANGO_HTTPS"):
            environment.pop(name, None)
        environment.update(DJANGO_SECRET_KEY="fictional-settings-test", **values)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from config import settings; "
                "print(json.dumps([settings.DEMO_MODE, settings.SHARED_DEMO]))",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_production_configuration_passes_the_existing_no_demo_guard(self):
        self.assertEqual(
            self.mode(ME_SHARED_DEMO="0", DJANGO_HTTPS="1"), [False, False]
        )

    def test_demo_is_disabled_by_default_even_with_https(self):
        self.assertEqual(self.mode(), [False, False])
        self.assertEqual(self.mode(DJANGO_HTTPS="1"), [False, False])

    def test_shared_previews_and_local_demo_remain_explicitly_available(self):
        self.assertEqual(self.mode(ME_SHARED_DEMO="1"), [True, True])
        self.assertEqual(self.mode(ME_DEMO_MODE="1"), [True, False])
        self.assertEqual(
            self.mode(ME_DEMO_MODE="0", ME_SHARED_DEMO="1"), [False, False]
        )


@override_settings(DEMO_MODE=False, SHARED_DEMO=False)
class NonDemoTests(TestCase):
    def test_previous_authenticated_demo_session_cannot_open_dashboard(self):
        user = get_user_model().objects.create_user(
            username="candidate@example.invalid"
        )
        Profile.objects.create(user=user, role="candidate", verified=True)
        Candidate.objects.create(user=user)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/dashboard/").status_code, 404)

    def test_previous_draft_session_cannot_open_profile(self):
        user = get_user_model().objects.create_user(username="draft@example.invalid")
        Profile.objects.create(user=user, role="candidate", verified=False)
        Candidate.objects.create(user=user)
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
            username="operator@example.invalid", password="fictional-test-password"
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_root_remains_available_without_demo_or_fictional_accounts(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertTemplateUsed(self.client.get("/"), "home.html")
        self.assertFalse(get_user_model().objects.exists())

    def test_demo_login_links_and_import_endpoints_are_unavailable(self):
        for path in ("/access/", "/confirm/fictional/", "/api/imports/"):
            for method in (self.client.get, self.client.post):
                with self.subTest(path=path, method=method.__name__):
                    self.assertEqual(method(path).status_code, 404)

    def test_demo_seed_cannot_create_fictional_accounts(self):
        with patch("config.demo.call_command") as seed:
            ensure_demo()
            seed.assert_not_called()
        with self.assertRaises(CommandError):
            call_command("seed_demo", verbosity=0)
        self.assertFalse(get_user_model().objects.exists())
