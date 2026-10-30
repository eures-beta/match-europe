from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse


class EntryPointTests(TestCase):
    @override_settings(SHARED_DEMO=True)
    def test_home_opens_the_public_home_with_both_journeys(self):
        response = self.client.get("/", secure=True)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, '<html lang="fr"')
        self.assertContains(response, 'href="/employer/pages/fr.html"')
        self.assertContains(response, 'href="/candidate/?lang=fr"')
        self.assertContains(
            self.client.get("/employer/pages/fr.html", secure=True), '<html lang="fr"'
        )

    @override_settings(SHARED_DEMO=True)
    def test_employer_landing_languages_remain_available(self):
        for language in ("fr", "en", "de"):
            with self.subTest(language=language):
                response = self.client.get(
                    f"/employer/pages/{language}.html", secure=True
                )
                self.assertContains(response, f'<html lang="{language}"')

    def test_role_access_remains_available(self):
        response = self.client.get("/access/")
        self.assertTemplateUsed(response, "access.html")
        self.assertContains(response, "bootstrap.min.css")

    def test_admin_requires_authentication(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, "/admin/login/?next=/admin/")

    def test_native_admin_with_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")
        user = get_user_model().objects.create_superuser(
            username="test-admin", password="fictional-test-password"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin:auth_user_changelist"))
