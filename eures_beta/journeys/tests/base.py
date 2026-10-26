import tempfile
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import override_settings
from eures_beta.journeys.models import Match


from django.test import TestCase


class JourneyScenario(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.users = {
            role: User.objects.get(profile__role=role)
            for role in ['adviser', 'employer', 'candidate', 'admin']
        }
        self.match = Match.objects.get()
        self.offer = self.match.offer

    def as_role(self, role):
        self.client.force_login(self.users[role])
