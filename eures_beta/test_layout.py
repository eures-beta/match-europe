from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class UnifiedLayoutTests(SimpleTestCase):
    def test_packaged_application_preserves_its_database_label(self):
        app = apps.get_app_config('journeys')
        self.assertEqual(app.name, 'eures_beta.journeys')
        self.assertEqual(app.get_model('Profile')._meta.db_table, 'journeys_profile')
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
