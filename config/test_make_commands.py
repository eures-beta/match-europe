"""Exercise the Make entry points without running a database or a second suite."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase


class MakeTestCommandsTests(SimpleTestCase):
    def setUp(self):
        self.make = shutil.which('make')
        if not self.make:
            self.skipTest('GNU Make is required to verify the command interface.')
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.record = self.root / 'calls.jsonl'
        self.makefile = Path(__file__).resolve().parents[1] / 'Makefile'
        # Capture arguments and one synthetic marker, never application settings.
        recorder = (
            f'#!{sys.executable}\n'
            'import json, os, sys\n'
            'with open(os.environ["MAKE_PROBE_RECORD"], "a") as output:\n'
            '    output.write(json.dumps(sys.argv[1:]) + "\\n")\n'
            'if "MAKE_PROBE_SETTING" in os.environ:\n'
            '    with open(os.environ["MAKE_PROBE_RECORD"] + ".setting", "w") as output:\n'
            '        output.write(os.environ["MAKE_PROBE_SETTING"])\n'
            'sys.exit(int(os.environ.get("MAKE_PROBE_EXIT", "0")))\n'
        )
        for name in ('python-probe', 'node'):
            path = self.root / name
            path.write_text(recorder)
            path.chmod(0o700)

    def run_make(self, target='test', *, exit_code=0, **parameters):
        return subprocess.run(
            [
                self.make,
                '--no-print-directory',
                '-f',
                str(self.makefile),
                target,
                f'PYTHON={self.root / "python-probe"}',
                *(f'{name}={value}' for name, value in parameters.items()),
            ],
            cwd=self.root,
            env={
                **{
                    name: value
                    for name, value in os.environ.items()
                    if name
                    not in {
                        'HOST',
                        'PORT',
                        'TESTS',
                        'TEST_ARGS',
                        'JS_TESTS',
                        'PYTHON',
                        'MAKEFLAGS',
                        'MAKEOVERRIDES',
                        'MFLAGS',
                    }
                },
                'PATH': str(self.root) + os.pathsep + os.environ.get('PATH', ''),
                'MAKE_PROBE_RECORD': str(self.record),
                'MAKE_PROBE_EXIT': str(exit_code),
                'MAKEFLAGS': '',
                'MAKEOVERRIDES': '',
            },
            capture_output=True,
            text=True,
            timeout=10,
        )

    def calls(self):
        return [json.loads(line) for line in self.record.read_text().splitlines()]

    def test_default_keeps_the_entire_django_suite(self):
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls(),
            [
                [
                    'manage.py',
                    'test',
                    'eures_beta',
                    'config',
                    '--noinput',
                    '--verbosity=0',
                ]
            ],
        )

    def test_selected_modules_replace_defaults_in_one_runner(self):
        result = self.run_make(
            TESTS='eures_beta.matching eures_beta.skills',
            TEST_ARGS='--keepdb --verbosity=2 -k albert',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls(),
            [
                [
                    'manage.py',
                    'test',
                    'eures_beta.matching',
                    'eures_beta.skills',
                    '--noinput',
                    '--keepdb',
                    '--verbosity=2',
                    '-k',
                    'albert',
                ]
            ],
        )

    def test_class_and_method_labels_are_forwarded(self):
        for suffix in ('AccountPageTests', 'AccountPageTests.test_anonymous'):
            with self.subTest(label=suffix):
                label = 'eures_beta.users.tests.test_account.' + suffix
                result = self.run_make(TESTS=label)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.calls()[-1][2:-2], [label])

    def test_filter_does_not_remove_default_discovery(self):
        result = self.run_make(TEST_ARGS='-k albert')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls(),
            [
                [
                    'manage.py',
                    'test',
                    'eures_beta',
                    'config',
                    '--noinput',
                    '-k',
                    'albert',
                ]
            ],
        )

    def test_runner_failure_remains_a_make_failure(self):
        result = self.run_make(exit_code=17)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 1)

    def test_javascript_discovery_includes_both_filename_conventions(self):
        files = (
            'eures_beta/users/tests/navigation.test.cjs',
            'eures_beta/occupations/test_picker.cjs',
        )
        for name in (*files, 'eures_beta/static/application.js'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        result = self.run_make('test-js')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['--test', *sorted(files)]])

    def test_javascript_selection_runs_only_the_selected_file(self):
        result = self.run_make('test-js', JS_TESTS='selected.test.cjs')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['--test', 'selected.test.cjs']])

    def test_empty_selection_is_rejected_before_starting_a_runner(self):
        for target, parameter in (('test', 'TESTS'), ('test-js', 'JS_TESTS')):
            with self.subTest(target=target):
                result = self.run_make(target, **{parameter: ''})
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.record.exists())

    def test_run_defaults_to_loopback_port_8000(self):
        result = self.run_make('run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['manage.py', 'runserver', '127.0.0.1:8000']])

    def test_run_forwards_port_host_and_loads_worktree_configuration(self):
        (self.root / '.env').write_text('MAKE_PROBE_SETTING=worktree-local\n')
        result = self.run_make('run', HOST='localhost', PORT='9047')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['manage.py', 'runserver', 'localhost:9047']])
        self.assertEqual(
            Path(str(self.record) + '.setting').read_text(), 'worktree-local'
        )

    def test_run_propagates_server_failure(self):
        result = self.run_make('run', PORT='9047', exit_code=17)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 1)
