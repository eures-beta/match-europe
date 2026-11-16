"""Version selection must never propose a prerelease or downgrade."""

import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from config.python_runtime import image_digest, latest_version, main


def refs(*versions):
    return [{'ref': f'refs/tags/v{version}'} for version in versions]


class PythonRuntimeTests(unittest.TestCase):
    def test_new_minor_and_patch_selected_numerically(self):
        self.assertEqual(
            latest_version(refs('3.9.9', '3.14.9', '3.15.0', '3.15.10'), '3.14'),
            '3.15.10',
        )

    def test_patch_updates_after_exact_pin(self):
        self.assertEqual(latest_version(refs('3.15.1'), '3.15.0'), '3.15.1')

    def test_minor_declaration_becomes_an_exact_patch(self):
        self.assertEqual(latest_version(refs('3.14.10'), '3.14'), '3.14.10')

    def test_no_prereleases_or_downgrades(self):
        self.assertIsNone(
            latest_version(refs('3.14.0', '3.15.0rc1', '3.16.0a1'), '3.14.10')
        )

    def test_missing_stable_metadata_fails_closed(self):
        with self.assertRaises(ValueError):
            latest_version(refs('3.16.0a1'), '3.14')

    def test_invalid_version_never_contacts_registry(self):
        with patch('config.python_runtime.read_https') as request:
            with self.assertRaises(ValueError):
                image_digest('3.15.0; echo unsafe')
            request.assert_not_called()

    def test_incomplete_image_fails_closed(self):
        with patch(
            'config.python_runtime.read_https',
            side_effect=[b'{"token":"public-pull-token"}', b'{"manifests":[]}'],
        ):
            with self.assertRaises(ValueError):
                image_digest('3.15.0')

    def test_manifest_is_hashed_and_supports_both_architectures(self):
        manifest = json.dumps(
            {
                'manifests': [
                    {'platform': {'os': 'linux', 'architecture': architecture}}
                    for architecture in ('amd64', 'arm64')
                ]
            }
        ).encode()
        with patch(
            'config.python_runtime.read_https',
            side_effect=[b'{"token":"public-pull-token"}', manifest],
        ):
            self.assertEqual(
                image_digest('3.15.0'),
                'sha256:' + hashlib.sha256(manifest).hexdigest(),
            )

    def test_failed_registry_resolution_does_not_write_either_lock_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.python-version').write_text('3.14\n')
            (root / '.python-image-digest').write_text('old-digest\n')
            with (
                patch('config.python_runtime.ROOT', root),
                patch('sys.argv', ['python_runtime', '--update']),
                patch('config.python_runtime.subprocess.run') as github,
                patch('config.python_runtime.image_digest', side_effect=ValueError),
            ):
                github.return_value.stdout = json.dumps(refs('3.15.0'))
                with self.assertRaises(ValueError):
                    main()
            self.assertEqual((root / '.python-version').read_text(), '3.14\n')
            self.assertEqual(
                (root / '.python-image-digest').read_text(), 'old-digest\n'
            )
