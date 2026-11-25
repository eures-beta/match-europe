"""Version selection must never propose a prerelease or downgrade."""

import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from config.python_runtime import (
    clever_python_versions,
    image_digest,
    latest_version,
    main,
)


def refs(*versions):
    return [{'ref': f'refs/tags/v{version}'} for version in versions]


def catalogue(*values):
    rows = ''.join(f'<tr><td></td><td><code>{v}</code></td></tr>' for v in values)
    return (
        '<table><tr><th>Default Version</th><th>Accepted Versions</th></tr>'
        + rows
        + '</table>'
    )


class PythonRuntimeTests(unittest.TestCase):
    def test_official_table_excludes_aliases_and_end_of_life_versions(self):
        self.assertEqual(
            clever_python_versions(catalogue('2', '3', '3.9 (EOL)', '3.13', '3.14')),
            {'3.13', '3.14'},
        )

    def test_unrelated_versions_in_examples_are_not_support_evidence(self):
        self.assertEqual(
            clever_python_versions('<pre>Python 3.15</pre>' + catalogue('3.14')),
            {'3.14'},
        )

    def test_missing_ambiguous_or_changed_catalogue_fails_closed(self):
        for html in (
            '<html>Service unavailable</html>',
            catalogue('3.14') * 2,
            catalogue('3.15 beta'),
            catalogue('3.14 (EOL)'),
            catalogue('3'),
            catalogue('3.14').replace('</table>', ''),
            catalogue('3.14').replace('<td></td>', ''),
        ):
            with self.subTest(html=html), self.assertRaises(ValueError):
                clever_python_versions(html)

    def test_selects_supported_patch_instead_of_newer_unsupported_minor(self):
        self.assertEqual(
            latest_version(refs('3.14.2', '3.15.2'), '3.14', {'3.14'}), '3.14.2'
        )
        self.assertIsNone(latest_version(refs('3.15.2'), '3.14', {'3.14'}))
        self.assertIsNone(latest_version(refs('3.14.2', '3.15.2'), '3.15.1', {'3.14'}))

    def test_clever_gate_precedes_registry_and_writes(self):
        for response in (catalogue('3.13'), '<html>Unavailable</html>'):
            with self.subTest(response=response), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / '.python-version').write_text('3.14\n')
                (root / '.python-image-digest').write_text('old-digest\n')
                with (
                    patch('config.python_runtime.ROOT', root),
                    patch('sys.argv', ['python_runtime', '--update']),
                    patch('config.python_runtime.subprocess.run') as github,
                    patch(
                        'config.python_runtime.read_https',
                        return_value=response.encode(),
                    ),
                    patch('config.python_runtime.image_digest') as registry,
                ):
                    github.return_value.stdout = json.dumps(refs('3.15.2'))
                    if response.startswith('<html>'):
                        with self.assertRaises(ValueError):
                            main()
                    else:
                        main()
                    registry.assert_not_called()
                self.assertEqual((root / '.python-version').read_text(), '3.14\n')
                self.assertEqual(
                    (root / '.python-image-digest').read_text(), 'old-digest\n'
                )

    def test_clever_network_failure_does_not_write_or_contact_registry(self):
        with (
            patch('sys.argv', ['python_runtime', '--update']),
            patch('config.python_runtime.subprocess.run') as github,
            patch('config.python_runtime.read_https', side_effect=OSError('offline')),
            patch('config.python_runtime.image_digest') as registry,
            patch.object(Path, 'write_text') as write,
        ):
            github.return_value.stdout = json.dumps(refs('3.15.2'))
            with self.assertRaises(OSError):
                main()
            registry.assert_not_called()
            write.assert_not_called()

    def test_update_writes_only_the_latest_clever_supported_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.python-version').write_text('3.14\n')
            (root / '.python-image-digest').write_text('old-digest\n')
            with (
                patch('config.python_runtime.ROOT', root),
                patch('sys.argv', ['python_runtime', '--update']),
                patch('config.python_runtime.subprocess.run') as github,
                patch(
                    'config.python_runtime.read_https',
                    return_value=catalogue('3.14').encode(),
                ),
                patch(
                    'config.python_runtime.image_digest', return_value='new-digest'
                ) as registry,
            ):
                github.return_value.stdout = json.dumps(refs('3.14.2', '3.15.2'))
                main()
                registry.assert_called_once_with('3.14.2')
            self.assertEqual((root / '.python-version').read_text(), '3.14.2\n')
            self.assertEqual(
                (root / '.python-image-digest').read_text(), 'new-digest\n'
            )

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
                patch(
                    'config.python_runtime.clever_python_versions',
                    return_value={'3.15'},
                ),
                patch('config.python_runtime.read_https', return_value=b'catalogue'),
                patch('config.python_runtime.image_digest', side_effect=ValueError),
            ):
                github.return_value.stdout = json.dumps(refs('3.15.0'))
                with self.assertRaises(ValueError):
                    main()
            self.assertEqual((root / '.python-version').read_text(), '3.14\n')
            self.assertEqual(
                (root / '.python-image-digest').read_text(), 'old-digest\n'
            )
