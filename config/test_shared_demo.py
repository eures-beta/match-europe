from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone, translation

from config.demo import ensure_demo
from eures_beta.journeys.employer_api import aglae
from eures_beta.journeys.models import EmployerImport
from eures_beta.journeys.offer_ingestion import ImportFailure


@override_settings(SHARED_DEMO=True, DEMO_MODE=True)
class SharedDemoTests(TestCase):
    def test_fictional_seed_is_initialized_once_and_edits_survive_restart(self):
        ensure_demo()
        user = get_user_model().objects.get(username="admin@example.invalid")
        profile = user.profile
        profile.name = "Fictional review in progress"
        profile.save()
        ensure_demo()
        profile.refresh_from_db()
        self.assertEqual(profile.name, "Fictional review in progress")
        self.assertEqual(get_user_model().objects.count(), 4)

    def test_remote_https_can_open_preview_but_http_is_not_enabled(self):
        response = self.client.get(
            "/previews/employer-landing/import-v2-fr.html",
            secure=True,
            REMOTE_ADDR="192.0.2.42",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-live-local="true"')
        self.assertEqual(
            self.client.get(
                "/local-api/imports/", REMOTE_ADDR="192.0.2.42"
            ).status_code,
            404,
        )

    def test_shared_push_diagnostic_stays_disabled_even_on_loopback(self):
        with patch.dict("os.environ", {"ME_EMPLOYER_LOCAL_API": "1"}):
            self.assertEqual(
                self.client.get(
                    "/local-api/push-test/config/", secure=True
                ).status_code,
                404,
            )

    def test_remote_api_retains_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/local-api/imports/", secure=True, REMOTE_ADDR="192.0.2.42"
            ).status_code,
            403,
        )

    def test_drafts_remain_owned_by_their_browser_session(self):
        session = self.client.session
        session.save()
        draft = EmployerImport.objects.create(
            session_key=session.session_key,
            email="fictional@example.invalid",
            source_kind="manual",
            data={"title": "Fictional draft"},
            preparation_agreed_at=timezone.now(),
        )
        path = f"/local-api/imports/{draft.pk}/"
        self.assertEqual(self.client.get(path, secure=True).status_code, 200)
        self.assertEqual(Client().get(path, secure=True).status_code, 404)

    def test_shared_demo_never_reads_sandbox_key_or_calls_aglae(self):
        with (
            patch("eures_beta.journeys.employer_api.Path.read_text") as key,
            patch("eures_beta.journeys.employer_api.build_opener") as network,
        ):
            with self.assertRaises(ImportFailure):
                aglae("POST", "job-posting", {})
            key.assert_not_called()
            network.assert_not_called()

    def test_notice_is_available_in_each_interface_language(self):
        from eures_beta.journeys.demo import shared_notice

        for language, expected in [
            ('fr', 'Démonstration partagée'),
            ('en', 'Shared demonstration'),
            ('de', 'Geteilte Demonstration'),
        ]:
            with translation.override(language):
                self.assertIn(expected, shared_notice())
            response = self.client.get(
                f"/previews/employer-landing/import-v2-{language}.html", secure=True
            )
            self.assertContains(response, expected)
