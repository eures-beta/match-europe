from django.test import TestCase, Client
from django.core.management import call_command
from django.conf import settings
class IncrementTests(TestCase):
    def test_configuration_and_schema(self):
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(self.client.get('/').status_code,200)
        from journeys.models import Profile
        self.assertEqual(Profile.objects.count(), 0)
