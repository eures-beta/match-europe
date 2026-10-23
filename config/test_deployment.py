import re
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.db import OperationalError
from django.test import Client, SimpleTestCase, TestCase, override_settings


class CollectedStaticTests(SimpleTestCase):
    def test_wsgi_serves_home_and_collected_css_without_debug(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(STATIC_ROOT=directory, DEBUG=False):
                call_command("collectstatic", interactive=False, verbosity=0)
                client = Client()
                home = client.get("/")
                self.assertEqual(home.status_code, 200)
                css_path = re.search(
                    r'href="([^"]+bootstrap.min.css)"', home.content.decode()
                )[1]
                for path in (css_path, "/static/admin/css/base.css"):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200, path)
                    self.assertTrue(response["Content-Type"].startswith("text/css"))
                    self.assertGreater(len(b"".join(response.streaming_content)), 100)
                    response.close()

    @override_settings(
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        SECURE_SSL_REDIRECT=True,
    )
    def test_https_ingress_does_not_create_a_redirect_loop(self):
        client = Client()
        self.assertEqual(
            client.get("/", HTTP_X_FORWARDED_PROTO="https").status_code, 200
        )
        self.assertRedirects(
            client.get("/"),
            "https://testserver/",
            status_code=301,
            fetch_redirect_response=False,
        )


class HealthTests(TestCase):
    @override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=True)
    def test_probe_accepts_an_instance_ip_without_relaxing_other_routes(self):
        response = self.client.get("/health/", HTTP_HOST="192.0.2.17:8080")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertNotIn("Location", response)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(
            self.client.head("/health/", HTTP_HOST="192.0.2.17:8080").status_code, 204
        )
        self.assertEqual(
            self.client.post("/health/", HTTP_HOST="192.0.2.17:8080").status_code, 405
        )
        for path in ("/", "/admin/", "/health/anything"):
            self.assertEqual(
                self.client.get(path, HTTP_HOST="192.0.2.17:8080").status_code, 400
            )

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_checks_postgresql_without_https_redirect_or_cache(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post("/health/").status_code, 405)

    def test_failed_database_returns_no_internal_details(self):
        with patch(
            "config.health.connection.cursor",
            side_effect=OperationalError("fictional-secret"),
        ):
            response = self.client.get("/health/", HTTP_HOST="probe.example.invalid")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b"")
