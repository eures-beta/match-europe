from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse


class SkeletonTests(TestCase):
    def test_home_opens_the_prototype_access_page(self):
        self.assertRedirects(self.client.get("/"), "/access/")
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
