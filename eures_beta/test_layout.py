from django.apps import apps
from django.conf import settings
from django.test import TestCase, override_settings


class UnifiedLayoutTests(TestCase):
    def test_only_current_applications_remain(self):
        for label in (
            'journeys',
            'accounts',
            'offers',
            'matching',
            'conversations',
            'notifications',
        ):
            self.assertNotIn(label, apps.app_configs)
            self.assertFalse((settings.APPS_DIR / label).exists())
        self.assertFalse((settings.APPS_DIR / 'migration_history').exists())
        self.assertEqual(settings.ROOT_URLCONF, 'config.urls')
        self.assertFalse((settings.APPS_DIR / 'manage.py').exists())
        self.assertFalse((settings.APPS_DIR / 'config').exists())

    def test_service_worker_uses_the_shared_static_directory(self):
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            (settings.APPS_DIR / 'static' / 'sw.js').read_bytes(),
        )

    @override_settings(SHARED_DEMO=True)
    def test_employer_pages_are_django_templates_and_sources_are_not_exposed(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(
            get_user_model().objects.create_user(
                email="importer@example.invalid", kind="employer"
            )
        )
        for language in ("fr", "en", "de"):
            for prefix in ("", "import-", "import-v2-", "privacy-"):
                page = prefix + language + ".html"
                response = self.client.get("/employer/pages/" + page, secure=True)
                self.assertEqual(response.status_code, 200, page)
                self.assertTemplateUsed(
                    response,
                    "employer/"
                    + (prefix.rstrip("-") + ".html" if prefix else "landing.html"),
                )
        for source in ("build.cjs", "copy.json", "../base.html", "offer-import-api.js"):
            self.assertEqual(
                self.client.get("/employer/pages/" + source, secure=True).status_code,
                404,
            )
