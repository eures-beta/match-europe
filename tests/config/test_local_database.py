"""Local preparation contracts: no fallback, no grants, no existing-data writes."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
import psycopg

from config.local_database import LocalDatabase, DatabasePreparationError, main

ENVIRONMENT = {
    'PGHOST': '/tmp',
    'PGPORT': '5432',
    'PGUSER': 'developer',
    'PGDATABASE': 'match_worktree',
    'DJANGO_ENVIRONMENT': 'local',
}


class LocalDatabaseTests(SimpleTestCase):
    def configuration(self, **changes):
        with patch.dict(os.environ, {**ENVIRONMENT, **changes}, clear=True):
            return LocalDatabase.from_environment()

    def connection(
        self, *, exists=True, owner='developer', can_create=True, can_connect=True
    ):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        state = {'exists': exists}

        def execute(statement, parameters=None):
            cursor = MagicMock()
            if isinstance(statement, str) and statement.startswith(
                'SELECT current_user'
            ):
                cursor.fetchone.return_value = ('developer', can_create)
            elif isinstance(statement, str) and statement.startswith(
                'SELECT pg_get_userbyid'
            ):
                cursor.fetchone.return_value = (
                    (owner, can_connect) if state['exists'] else None
                )
            elif not isinstance(statement, str):
                state['exists'] = True
            return cursor

        connection.execute.side_effect = execute
        return connection

    def run_preparation(self, connection, *, create=False):
        database = self.configuration()
        with (
            patch.object(LocalDatabase, 'connect', return_value=connection),
            redirect_stdout(StringIO()),
        ):
            database.run(create=create)

    def test_connection_parameters_never_fall_back_to_another_instance_or_role(self):
        database = self.configuration()
        with patch('config.local_database.psycopg.connect') as connect:
            database.connect()
        self.assertEqual(
            connect.call_args.kwargs,
            {
                'host': '/tmp',
                'port': 5432,
                'user': 'developer',
                'dbname': 'postgres',
                'connect_timeout': 5,
                'application_name': 'match-europe-local-database',
                'autocommit': True,
            },
        )

    def test_missing_parameters_are_explicit_and_not_inferred_from_os_user(self):
        for name in ('PGHOST', 'PGPORT', 'PGUSER', 'PGDATABASE'):
            with (
                self.subTest(parameter=name),
                self.assertRaisesRegex(DatabasePreparationError, name),
            ):
                self.configuration(**{name: ''})

    def test_remote_production_system_databases_and_invalid_ports_are_rejected(self):
        for changes in (
            {'PGHOST': 'database.example.invalid'},
            {'DJANGO_ENVIRONMENT': 'production'},
            {'PGDATABASE': 'postgres'},
            {'PGDATABASE': 'template1'},
            {'PGDATABASE': 'x' * 59},
            {'PGPORT': 'not-a-port'},
            {'PGPORT': '0'},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(DatabasePreparationError),
            ):
                self.configuration(**changes)

    def test_check_is_read_only_and_checks_the_configured_database(self):
        connection = self.connection()
        self.run_preparation(connection)
        statements = [call.args[0] for call in connection.execute.call_args_list]
        self.assertEqual(statements[0], 'SET default_transaction_read_only = on')
        self.assertTrue(
            all(
                isinstance(statement, str)
                and not statement.startswith(('CREATE', 'ALTER', 'DROP'))
                for statement in statements
            )
        )
        self.assertEqual(
            [
                call.args[1]
                for call in connection.execute.call_args_list
                if len(call.args) > 1
            ],
            [('match_worktree',)],
        )

    def test_missing_database_in_check_instructs_creation_without_creating_it(self):
        connection = self.connection(exists=False)
        with self.assertRaisesRegex(DatabasePreparationError, 'make db-create'):
            self.run_preparation(connection)
        self.assertTrue(
            all(
                isinstance(call.args[0], str)
                for call in connection.execute.call_args_list
            )
        )

    def test_create_is_idempotent_and_does_not_touch_an_existing_database(self):
        connection = self.connection()
        self.run_preparation(connection, create=True)
        self.run_preparation(connection, create=True)
        self.assertTrue(
            all(
                isinstance(call.args[0], str)
                for call in connection.execute.call_args_list
            )
        )

    def test_create_quotes_the_database_identifier_and_never_creates_a_role(self):
        connection = self.connection(exists=False)
        with (
            patch.dict(
                os.environ, {**ENVIRONMENT, 'PGDATABASE': 'quoted"; name'}, clear=True
            ),
            patch.object(LocalDatabase, 'connect', return_value=connection),
            redirect_stdout(StringIO()),
        ):
            LocalDatabase.from_environment().run(create=True)
        statements = [call.args[0] for call in connection.execute.call_args_list]
        writes = [
            statement.as_string()
            for statement in statements
            if not isinstance(statement, str)
        ]
        self.assertEqual(writes, ['CREATE DATABASE "quoted""; name"'])

    def test_insufficient_create_privilege_or_wrong_owner_never_triggers_creation(self):
        for parameters in (
            {'can_create': False},
            {'owner': 'another_role'},
            {'can_connect': False},
        ):
            connection = self.connection(**parameters)
            with (
                self.subTest(parameters=parameters),
                self.assertRaises(DatabasePreparationError),
            ):
                self.run_preparation(connection, create=True)
            self.assertTrue(
                all(
                    isinstance(call.args[0], str)
                    for call in connection.execute.call_args_list
                )
            )

    def test_connection_error_is_sanitized_without_retrying_another_user(self):
        output = StringIO()
        with (
            patch.dict(os.environ, ENVIRONMENT, clear=True),
            patch('sys.argv', ['db', 'check']),
            patch.object(
                LocalDatabase,
                'connect',
                side_effect=psycopg.OperationalError('password=private-sentinel'),
            ) as connect,
            redirect_stderr(output),
        ):
            self.assertEqual(main(), 1)
        self.assertEqual(connect.call_count, 1)
        self.assertNotIn('private-sentinel', output.getvalue())
        self.assertIn('Aucun autre serveur', output.getvalue())


class LocalDatabaseMakeTests(SimpleTestCase):
    def test_failed_preflight_stops_make_test_before_the_django_runner(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / 'calls'
            runner = root / 'python-probe'
            runner.write_text(
                f'#!{sys.executable}\n'
                'import sys\n'
                f'with open({str(record)!r}, "a") as output: output.write(repr(sys.argv[1:]) + "\\n")\n'
                'sys.exit(7)\n'
            )
            runner.chmod(0o700)
            project = Path(__file__).resolve().parents[2]
            makefile = root / 'Makefile'
            shutil.copyfile(project / 'Makefile', makefile)
            shutil.copytree(project / 'mk', root / 'mk')
            shutil.copyfile(project / '.python-version', root / '.python-version')
            result = subprocess.run(
                [
                    'make',
                    '--no-print-directory',
                    '-f',
                    str(makefile),
                    'test',
                    f'PYTHON={runner}',
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, 'MAKEFLAGS': '', 'MAKEOVERRIDES': '', 'MFLAGS': ''},
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                record.read_text().splitlines(),
                ["['-m', 'config.local_database', 'check']"],
            )
