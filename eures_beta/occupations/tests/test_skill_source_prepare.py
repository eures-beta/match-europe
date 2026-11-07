import hashlib
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings

MODULE = 'eures_beta.occupations.management.commands.prepare_skill_source.'


class SourcePreparationTests(SimpleTestCase):
    def test_missing_archives_require_explicit_download(self):
        with (
            TemporaryDirectory() as directory,
            override_settings(SKILLS_ALBERT_SOURCE_DIR=directory),
            patch(MODULE + 'urlopen') as network,
        ):
            with self.assertRaises(CommandError):
                call_command('prepare_skill_source', stdout=StringIO())
            network.assert_not_called()

    def test_only_verified_download_is_promoted(self):
        value = b'fictional-official-archive'
        response = MagicMock()
        response.read.side_effect = [value, b'']
        with (
            TemporaryDirectory() as directory,
            override_settings(SKILLS_ALBERT_SOURCE_DIR=directory),
            patch(MODULE + 'PINNED', {'fr': hashlib.sha256(value).hexdigest()}),
            patch(MODULE + 'urlopen') as network,
            patch(MODULE + 'load_source', return_value=({}, {})),
        ):
            network.return_value.__enter__.return_value = response
            call_command('prepare_skill_source', download=True, stdout=StringIO())
            self.assertEqual(
                (Path(directory) / 'esco-1.2.1-fr.zip').read_bytes(), value
            )
            self.assertTrue(
                network.call_args.args[0].startswith(
                    'https://ec.europa.eu/esco/download/'
                )
            )
            self.assertEqual(network.call_args.kwargs['timeout'], 45)

    def test_bad_checksum_does_not_leave_a_partial_archive(self):
        response = MagicMock()
        response.read.side_effect = [b'corrupted', b'']
        with (
            TemporaryDirectory() as directory,
            override_settings(SKILLS_ALBERT_SOURCE_DIR=directory),
            patch(MODULE + 'PINNED', {'fr': '0' * 64}),
            patch(MODULE + 'urlopen') as network,
        ):
            network.return_value.__enter__.return_value = response
            with self.assertRaises(CommandError):
                call_command('prepare_skill_source', download=True, stdout=StringIO())
            self.assertEqual(list(Path(directory).iterdir()), [])
