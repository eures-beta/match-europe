"""Verify the actual environment contract in isolated processes."""

import json
import os
import subprocess
import sys
from django.test import SimpleTestCase


class EnvironmentParitySettingsTests(SimpleTestCase):
    def probe(self, environment, **configuration):
        values = os.environ.copy()
        values.pop('ALBERT_SIMULATED', None)
        values.update(
            DJANGO_ENVIRONMENT=environment,
            DJANGO_SECRET_KEY='fictional-parity-settings',
            EMAIL_DELIVERY_ENABLED='0',
            TEST_ACCOUNTS_ENABLED='0',
            ALBERT_API_KEY='fictional-key',
        )
        values.update(configuration)
        result = subprocess.run(
            [
                sys.executable,
                '-c',
                'import django, json; django.setup(); '
                'from django.conf import settings; '
                'from eures_beta.employers.offer_structuring import enabled as offer; '
                'from eures_beta.skills.albert_skills import enabled as skills; '
                'from eures_beta.matching.dialogue_services import enabled as dialogue; '
                'print(json.dumps([offer(), skills(), dialogue(), '
                'settings.ALBERT_SIMULATED, settings.EMAIL_DELIVERY_ENABLED, '
                'settings.EMPLOYER_ADVISER_CONTACT_URL]))',
            ],
            env={**values, 'DJANGO_SETTINGS_MODULE': 'config.settings'},
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_business_services_are_available_in_every_environment(self):
        for environment in ('local', 'preview', 'production'):
            with self.subTest(environment=environment):
                self.assertEqual(
                    self.probe(environment)[:5], [True, True, True, False, False]
                )

    def test_one_simulation_switch_covers_all_albert_services_without_a_key(self):
        for environment in ('local', 'preview', 'production'):
            with self.subTest(environment=environment):
                result = self.probe(
                    environment, ALBERT_SIMULATED='1', ALBERT_API_KEY=''
                )
                self.assertEqual(result[:5], [True, True, True, True, False])

    def test_contact_uses_the_same_environment_and_setting_name(self):
        result = self.probe(
            'local', EMPLOYER_ADVISER_CONTACT_URL='https://example.invalid/contact'
        )
        self.assertEqual(result[5], 'https://example.invalid/contact')
