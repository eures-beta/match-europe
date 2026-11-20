import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from django.test import SimpleTestCase
from eures_beta.skills import common_source


class CommonLabelTests(SimpleTestCase):
    def test_requested_translations_unknown_keys_and_corrupt_suffix(self):
        labels = {'skill:one': {'fr': 'un', 'en': 'one', 'de': 'eins'}}
        raw = json.dumps(labels).encode()
        manifest = {'files': {'labels.json': hashlib.sha256(raw).hexdigest()}}
        with TemporaryDirectory() as directory:
            path = Path(directory)
            try:
                with (
                    patch.object(common_source, 'DATA', path),
                    patch.object(common_source, 'manifest', return_value=manifest),
                ):
                    with ZipFile(path / 'common_skill_source.zip', 'w') as archive:
                        archive.writestr('labels.json', raw)
                    common_source.skill_labels.cache_clear()
                    for language, expected in labels['skill:one'].items():
                        self.assertEqual(
                            common_source.skill_label('skill:one', language), expected
                        )
                    self.assertEqual(common_source.skill_label('unknown', 'fr'), '')
                    # A valid requested prefix cannot hide a changed suffix.
                    with ZipFile(path / 'common_skill_source.zip', 'w') as archive:
                        archive.writestr('labels.json', raw + b' ')
                    common_source.skill_labels.cache_clear()
                    with self.assertRaisesRegex(ValueError, 'checksum'):
                        common_source.skill_label('skill:one', 'fr')
            finally:
                common_source.skill_labels.cache_clear()
