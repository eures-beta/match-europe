"""The cached description must never survive a failed refresh."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from config.pr_description import ROOT, fetch_description


class PRDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    @patch('config.pr_description.subprocess.run')
    def test_success_preserves_unicode_and_literal_shell_text(self, github):
        body = '# Français\n$(echo texte) `texte` & fin\n'
        github.return_value.stdout = json.dumps({'body': body})
        target = fetch_description('195', self.root)
        self.assertEqual(target.read_text(), body)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('shell', github.call_args.kwargs)
        self.assertEqual(list(target.parent.iterdir()), [target])

    @patch('config.pr_description.subprocess.run')
    def test_failure_removes_previous_description_and_creates_no_empty_file(
        self, github
    ):
        runtime = self.root / '.runtime'
        runtime.mkdir()
        target = runtime / 'pr-195-description.md'
        target.write_text('ancienne description')
        github.side_effect = subprocess.CalledProcessError(1, 'gh', stderr='offline')
        with self.assertRaises(subprocess.CalledProcessError):
            fetch_description('195', self.root)
        self.assertEqual(list(runtime.iterdir()), [])

    @patch('config.pr_description.subprocess.run')
    def test_malformed_response_never_publishes_a_file(self, github):
        github.return_value.stdout = 'not JSON'
        with self.assertRaises(ValueError):
            fetch_description('195', self.root)
        self.assertEqual(list((self.root / '.runtime').iterdir()), [])

    @patch('config.pr_description.subprocess.run')
    def test_invalid_number_never_calls_github_or_creates_runtime(self, github):
        for number in ('', '-1', '../195', '195;echo unsafe', '$(echo unsafe)'):
            with self.subTest(number=number), self.assertRaises(ValueError):
                fetch_description(number, self.root)
        github.assert_not_called()
        self.assertFalse((self.root / '.runtime').exists())

    @patch('config.pr_description.subprocess.run')
    def test_empty_description_is_a_valid_github_result(self, github):
        github.return_value.stdout = '{"body":""}'
        self.assertEqual(fetch_description('195', self.root).read_text(), '')

    def test_make_does_not_evaluate_a_shell_expression_in_the_number(self):
        marker = self.root / 'must-not-exist'
        result = subprocess.run(
            ['make', 'pr-description', f'PR=$(shell touch {marker})'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('numéro de PR positif', result.stderr)
        self.assertFalse(marker.exists())
