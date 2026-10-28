from unittest.mock import patch
from django.core.management import call_command
from django.urls import reverse


from eures_beta.testing_support import DomainScenario


class DemoTests(DomainScenario):
    def test_demo_adapter_never_calls_network(self):
        with patch(
            'socket.create_connection', side_effect=AssertionError('Network forbidden')
        ):
            call_command('seed_demo', verbosity=0)
            self.as_role('adviser')
            self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
