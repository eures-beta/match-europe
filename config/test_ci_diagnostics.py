"""Exercise read-only diagnostics without GitHub, Django or PostgreSQL."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from config import ci_diagnostics as ci


def run_data(attempt=1):
    return {
        'databaseId': 123,
        'attempt': attempt,
        'status': 'completed',
        'conclusion': 'failure',
        'headSha': 'abc',
        'url': 'https://github.com/example/run',
        'jobs': [
            {
                'databaseId': 456,
                'name': 'Tests',
                'status': 'completed',
                'conclusion': 'failure',
                'url': 'https://github.com/example/job',
            },
            {
                'databaseId': 789,
                'name': 'Quality',
                'status': 'completed',
                'conclusion': 'success',
                'url': 'https://github.com/example/quality',
            },
        ],
    }


class CIDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = patch.object(ci, 'CACHE_ROOT', Path(self.temp.name) / 'cache')
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def invoke(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = ci.main(list(args))
        return result, out.getvalue(), err.getvalue()

    def test_default_filter_covers_test_failures_and_process_termination(self):
        log = 'normal\nAssertionError: mismatch\nnormal\nKilled\nmake: *** Error 137\nProcess completed with exit code 2.\n'
        with patch.object(
            ci, 'gh', side_effect=[json.dumps(run_data()).encode(), log.encode()]
        ) as gh:
            code, out, _ = self.invoke('errors', '--run', '123')
        self.assertEqual(code, 0)
        self.assertIn('AssertionError', out)
        self.assertIn('Killed', out)
        self.assertIn('Error 137', out)
        self.assertEqual(gh.call_count, 2)  # successful job not downloaded
        self.assertIn('GET', gh.call_args.args)

    def test_status_fetches_metadata_only(self):
        with patch.object(ci, 'gh', return_value=json.dumps(run_data()).encode()) as gh:
            code, out, _ = self.invoke('status', '--run', '123')
        self.assertEqual(code, 0)
        self.assertIn('Job 789', out)
        self.assertEqual(gh.call_count, 1)

    def test_repeated_filters_reuse_log_and_refresh_downloads(self):
        data = run_data()
        with (
            patch.object(ci, 'load_run', return_value=data),
            patch.object(ci, 'gh', return_value=b'ERROR: first\nKilled\n') as gh,
        ):
            self.invoke('errors', '--run', '123', '--pattern', 'ERROR')
            _, out, _ = self.invoke('errors', '--run', '123', '--pattern', 'Killed')
            self.assertIn('cache local', out)
            self.assertEqual(gh.call_count, 1)
            self.invoke('errors', '--run', '123', '--refresh')
            self.assertEqual(gh.call_count, 2)
        cached = next(ci.CACHE_ROOT.rglob('*.log'))
        self.assertEqual(cached.stat().st_mode & 0o777, 0o600)
        self.assertEqual(ci.CACHE_ROOT.stat().st_mode & 0o777, 0o700)

    def test_new_attempt_uses_different_cache(self):
        data = run_data()
        with patch.object(ci, 'gh', return_value=b'ERROR\n') as gh:
            ci.job_log('owner/repo', data, data['jobs'][0])
            data['attempt'] = 2
            ci.job_log('owner/repo', data, data['jobs'][0])
        self.assertEqual(gh.call_count, 2)

    def test_running_logs_are_not_cached(self):
        data = run_data()
        data['jobs'][0]['status'] = 'in_progress'
        with patch.object(ci, 'gh', return_value=b'ERROR\n') as gh:
            for _ in range(2):
                ci.job_log('owner/repo', data, data['jobs'][0])
        self.assertEqual(gh.call_count, 2)
        self.assertFalse(ci.CACHE_ROOT.exists())

    def test_unknown_job_does_not_fetch_logs(self):
        with (
            patch.object(ci, 'load_run', return_value=run_data()),
            patch.object(ci, 'gh') as gh,
        ):
            code, _, err = self.invoke('errors', '--run', '123', '--job', '999')
        self.assertEqual(code, 2)
        self.assertIn('ne fait pas partie', err)
        gh.assert_not_called()

    def test_empty_logs_are_error_and_not_cached(self):
        data = run_data()
        with patch.object(ci, 'gh', return_value=b''):
            with self.assertRaises(ci.DiagnosticError):
                ci.job_log('owner/repo', data, data['jobs'][0])
        self.assertFalse(ci.CACHE_ROOT.exists())

    def test_network_failure_is_not_no_matches_and_keeps_stderr_private(self):
        with patch.object(
            ci.subprocess,
            'run',
            return_value=subprocess.CompletedProcess([], 1, b'', b'secret credential'),
        ):
            code, out, err = self.invoke('errors', '--run', '123')
        self.assertEqual(code, 2)
        self.assertNotIn('Aucune ligne', out)
        self.assertNotIn('secret credential', err)
        self.assertIn('Lecture GitHub impossible', err)

    def test_timeout_and_missing_gh(self):
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired('gh', 90)):
            with (
                self.subTest(failure=failure),
                patch.object(ci.subprocess, 'run', side_effect=failure),
            ):
                with self.assertRaises(ci.DiagnosticError):
                    ci.gh('run', 'view')

    def test_bad_inputs_fail_before_network(self):
        invalid = [
            ('--run', '-1'),
            ('--run', '12; echo injected'),
            ('--run', '123', '--repo', '../repo'),
            ('--run', '123', '--repo', 'owner/repo/extra'),
            ('--run', '123', '--pattern', '['),
            ('--run', '123', '--context', '21'),
            ('--run', '123', '--lines', '0'),
        ]
        with patch.object(ci, 'gh') as gh:
            for args in invalid:
                with (
                    self.subTest(args=args),
                    self.assertRaises(SystemExit),
                    redirect_stderr(StringIO()),
                ):
                    ci.main(['errors', *args])
        gh.assert_not_called()

    def test_terminal_controls_removed_and_context_merged_bounded(self):
        log = '\x1b]0;title\x07\x1b[31mERROR one\x1b[0m\nERROR two\n\x00safe\n'
        out = StringIO()
        with redirect_stdout(out):
            ci.excerpt(log, re.compile('ERROR'), 1, 3)
        self.assertNotIn('\x1b', out.getvalue())
        self.assertNotIn('\x00', out.getvalue())
        self.assertEqual(out.getvalue().count('1: ERROR one'), 1)
        bounded = StringIO()
        with redirect_stdout(bounded):
            ci.excerpt(
                'ERROR first\nERROR second\nKilled', re.compile('ERROR|Killed'), 0, 2
            )
        self.assertNotIn('ERROR first', bounded.getvalue())
        self.assertIn('Killed', bounded.getvalue())
        self.assertIn('2 dernières lignes', bounded.getvalue())

    def test_no_matches_does_not_imply_success(self):
        out = StringIO()
        with redirect_stdout(out):
            ci.excerpt('everything quiet', re.compile('ERROR'), 0, 10)
        self.assertIn('ne prouve pas la réussite', out.getvalue())

    def test_metadata_invalid_or_wrong_run_fails(self):
        for payload in (
            b'bad JSON',
            b'{}',
            json.dumps({**run_data(), 'databaseId': 999}).encode(),
        ):
            with (
                self.subTest(payload=payload),
                patch.object(ci, 'gh', return_value=payload),
            ):
                with self.assertRaises(ci.DiagnosticError):
                    ci.load_run('owner/repo', 123)

    def test_make_preserves_pattern_as_data(self):
        # A regex containing quotes, dollars and a shell command is never evaluated.
        with tempfile.TemporaryDirectory() as directory:
            fake_python = Path(directory) / 'python3'
            fake_python.write_text('#!/bin/sh\nprintf "%s" "$CI_PATTERN"\n')
            fake_python.chmod(0o700)
            marker = Path(directory) / 'unexpected'
            pattern = f"Killed|'quoted'|$(shell touch {marker})"
            result = subprocess.run(
                [
                    'make',
                    '--no-print-directory',
                    'ci-errors',
                    'RUN=123',
                    f'PATTERN={pattern}',
                ],
                env={
                    **os.environ,
                    'PATH': f"{directory}:{os.defpath}",
                    'PATTERN': pattern,
                },
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(pattern, result.stdout)
            self.assertFalse(marker.exists())
