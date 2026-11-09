from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import TestCase, override_settings


class UnifiedLayoutTests(TestCase):
    def test_only_current_applications_remain(self):
        for label in (
            'journeys',
            'accounts',
            'offers',
            'conversations',
            'notifications',
        ):
            self.assertNotIn(label, apps.app_configs)
            self.assertFalse((settings.APPS_DIR / label).exists())
        # The retired prototype is gone; the new local-only engine is explicit.
        self.assertEqual(apps.get_app_config('matching').name, 'eures_beta.matching')
        self.assertFalse((settings.APPS_DIR / 'migration_history').exists())
        self.assertEqual(settings.ROOT_URLCONF, 'config.urls')
        self.assertFalse((settings.APPS_DIR / 'manage.py').exists())
        self.assertFalse((settings.APPS_DIR / 'config').exists())

    def test_public_and_candidate_pages_expose_installation(self):
        for url in ('/', '/candidate/', '/candidate/prepare/'):
            for language in ('fr', 'en', 'de'):
                with self.subTest(url=url, language=language):
                    response = self.client.get(url, {'lang': language}, follow=True)
                    self.assertContains(
                        response, 'rel="manifest" href="/manifest.webmanifest"'
                    )
                    self.assertContains(response, 'data-worker-url="/sw.js"')
                    self.assertContains(response, 'rel="apple-touch-icon"')

    def test_manifest_uses_static_icons_and_an_accessible_start_url(self):
        response = self.client.get('/manifest.webmanifest')
        self.assertEqual(response.headers['Content-Type'], 'application/manifest+json')
        manifest = response.json()
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(self.client.get(manifest['start_url']).status_code, 200)
        self.assertEqual(
            {icon['sizes'] for icon in manifest['icons']}, {'192x192', '512x512'}
        )
        for icon in manifest['icons']:
            size = icon['sizes'].split('x')[0]
            path = f'pwa/icon-{size}.png'
            self.assertEqual(icon['src'], static(path))
            self.assertIsNotNone(finders.find(path))

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
            for prefix in ("", "import-", "privacy-"):
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
