"""Exercise real settings, not just overrides, in every deployment environment."""

import json
import os
import subprocess
import sys
from django.test import SimpleTestCase


class EnvironmentParitySettingsTests(SimpleTestCase):
    def test_business_features_start_enabled_without_environment_exclusions(self):
        flags = [
            'ALBERT_IMPORT_ENABLED',
            'SKILLS_ALBERT_ENABLED',
            'CONTINUOUS_SKILLS_ENABLED',
            'MATCHING_ENABLED',
        ]
        for environment in ('local', 'preview', 'production'):
            values = os.environ.copy()
            for flag in flags:
                values.pop(flag, None)
            values.update(
                DJANGO_ENVIRONMENT=environment,
                DJANGO_SECRET_KEY='fictional-parity-settings',
                EMAIL_DELIVERY_ENABLED='1',
                TEST_ACCOUNTS_ENABLED='0',
            )
            with self.subTest(environment=environment):
                result = subprocess.run(
                    [
                        sys.executable,
                        '-c',
                        'import json; from config import settings; '
                        'print(json.dumps([getattr(settings, name) for name in '
                        + repr(flags)
                        + ']))',
                    ],
                    env=values,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(json.loads(result.stdout), [True] * len(flags))
