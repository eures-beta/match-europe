from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse


class EntryPointTests(TestCase):

    def test_home_opens_the_public_home_with_both_journeys(self):
        response = self.client.get("/", secure=True)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, '<html lang="fr"')
        self.assertContains(response, 'href="/employer/pages/fr.html"')
        self.assertContains(response, 'href="/candidate/?lang=fr"')
        self.assertContains(
            self.client.get("/employer/pages/fr.html", secure=True), '<html lang="fr"'
        )

    def test_employer_landing_languages_remain_available(self):
        for language in ("fr", "en", "de"):
            with self.subTest(language=language):
                response = self.client.get(
                    f"/employer/pages/{language}.html", secure=True
                )
                self.assertContains(response, f'<html lang="{language}"')

    def test_retired_role_access_is_unavailable(self):
        response = self.client.get("/access/")
        self.assertEqual(response.status_code, 404)

    def test_admin_requires_authentication(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(
            response, "/admin/login/?next=/admin/", fetch_redirect_response=False
        )
        self.assertRedirects(self.client.get(response.url), '/accounts/login/')

    def test_native_admin_with_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")
        user = get_user_model().objects.create_superuser(
            kind='adviser', email="test-admin", password="fictional-test-password"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin:users_user_changelist"))
