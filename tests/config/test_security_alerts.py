"""Review plans cannot become arbitrary API commands or silent bulk dismissals."""

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from config import security_alerts as tool


def alert(number=7, **changes):
    return dict(
        number=number,
        state='open',
        dismissed_reason=None,
        dismissed_comment=None,
        rule={'id': 'py/fictional-rule'},
        most_recent_instance={
            'commit_sha': 'a' * 40,
            'ref': 'refs/heads/main',
            'location': {'path': 'fictional/module.py', 'start_line': 42},
        },
        **changes,
    )


def plan(*numbers):
    return {
        'repository': tool.REPOSITORY,
        'alerts': [
            {
                'number': n,
                'expected': tool.snapshot(alert(n)),
                'state': 'dismissed',
                'reason': 'false positive',
                'comment': "Preuve d'analyse : https://github.com/eures-beta/match-europe/pull/229",
            }
            for n in (numbers or (7,))
        ],
    }


class FakeAPI:
    def __init__(self, *numbers):
        self.rows = {n: alert(n) for n in (numbers or (7,))}
        self.writes = []
        self.reads = []
        self.fail_on = None

    def __call__(self, endpoint, *, method='GET', payload=None):
        number = int(endpoint.rsplit('/', 1)[1])
        if method == 'GET':
            self.reads.append(number)
            return deepcopy(self.rows[number])
        if number == self.fail_on:
            raise tool.AlertError('Erreur réseau sans réessai.')
        self.writes.append((number, deepcopy(payload)))
        self.rows[number].update(payload)
        return deepcopy(self.rows[number])


class SecurityAlertTests(unittest.TestCase):
    def test_preview_is_read_only_and_no_decision_is_inferred(self):
        api = FakeAPI()
        preview = tool.prepare(plan(), api)
        self.assertEqual(api.writes, [])
        self.assertEqual(
            preview['changes'][0]['desired']['dismissed_reason'], 'false positive'
        )
        with self.assertRaises(tool.AlertError):
            tool.prepare(
                {
                    'repository': tool.REPOSITORY,
                    'alerts': [
                        {
                            'number': 7,
                            'expected': tool.snapshot(alert()),
                            'state': None,
                            'reason': None,
                            'comment': '',
                        }
                    ],
                },
                api,
            )
        self.assertEqual(api.writes, [])

    def test_entire_batch_is_validated_before_first_write(self):
        api = FakeAPI(7, 9)
        api.rows[9]['dismissed_comment'] = 'Another operator changed this alert.'
        with self.assertRaisesRegex(tool.AlertError, 'modifiée'):
            tool.apply(plan(7, 9), api, emit=lambda _: None)
        self.assertEqual(api.writes, [])

    def test_recheck_detects_change_after_preview(self):
        api = FakeAPI()
        calls = 0

        def concurrent(endpoint, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                api.rows[7]['state'] = 'fixed'
            return api(endpoint, **kwargs)

        with self.assertRaises(tool.AlertError):
            tool.apply(plan(), concurrent, emit=lambda _: None)
        self.assertEqual(api.writes, [])

    def test_apply_is_individual_and_safe_to_resume(self):
        api = FakeAPI(7, 9)
        api.fail_on = 9
        receipts = []
        with self.assertRaises(tool.AlertError):
            tool.apply(plan(7, 9), api, emit=receipts.append)
        self.assertEqual([n for n, _ in api.writes], [7])
        self.assertEqual(
            json.loads(receipts[-1]),
            {'event': 'applied', 'number': 7, 'state': 'dismissed'},
        )
        api.fail_on = None
        tool.apply(plan(7, 9), api, emit=lambda _: None)
        self.assertEqual([n for n, _ in api.writes], [7, 9])
        self.assertEqual(
            api.writes[0][1]['dismissed_comment'], plan()['alerts'][0]['comment']
        )

    def test_location_or_rule_change_is_refused_even_when_already_dismissed(self):
        for key in ('path', 'rule_id', 'commit_sha', 'ref'):
            with self.subTest(key=key):
                api = FakeAPI()
                tool.apply(plan(), api, emit=lambda _: None)
                changed = plan()
                changed['alerts'][0]['expected'][key] = 'another'
                with self.assertRaises(tool.AlertError):
                    tool.prepare(changed, api)
                self.assertEqual(len(api.writes), 1)

    def test_cannot_mark_fixed_or_change_another_repository_or_extra_fields(self):
        bad = []
        item = plan()
        item['repository'] = 'other/private'
        bad.append(item)
        item = plan()
        item['alerts'][0]['state'] = 'fixed'
        bad.append(item)
        item = plan()
        item['alerts'][0]['assignees'] = ['somebody']
        bad.append(item)
        item = plan()
        item['alerts'][0]['number'] = '../other'
        bad.append(item)
        item = plan()
        item['alerts'][0]['number'] = True
        bad.append(item)
        item = plan(7, 7)
        bad.append(item)
        item = plan()
        item['alerts'][0]['reason'] = 'acceptable risk'
        bad.append(item)
        item = plan()
        item['alerts'][0]['comment'] = ''
        bad.append(item)
        item = plan()
        item['alerts'][0]['comment'] = 'a' * 281
        bad.append(item)
        item = plan()
        item['alerts'][0]['comment'] = 'escape\x1b[31m'
        bad.append(item)
        item = plan()
        item['alerts'][0]['state'] = []
        bad.append(item)
        item = plan()
        item['alerts'][0]['reason'] = {}
        bad.append(item)
        for item in bad:
            with self.subTest(item=item), self.assertRaises(tool.AlertError):
                tool.validate(item)

    def test_reopen_sends_only_open_state_and_is_idempotent(self):
        api = FakeAPI()
        tool.apply(plan(), api, emit=lambda _: None)
        reopening = plan()
        item = reopening['alerts'][0]
        item.update(
            expected=tool.snapshot(api.rows[7]),
            state='open',
            reason=None,
            comment='Hypothèse changée ; réexaminer cette alerte.',
        )
        tool.apply(reopening, api, emit=lambda _: None)
        self.assertEqual(api.writes[-1][1], {'state': 'open'})
        tool.apply(reopening, api, emit=lambda _: None)
        self.assertEqual(len(api.writes), 2)

    def test_unconfirmed_response_stops_processing(self):
        api = FakeAPI()

        def protected(endpoint, **kwargs):
            if kwargs.get('method') == 'PATCH':
                return alert()
            return api(endpoint, **kwargs)

        with self.assertRaisesRegex(tool.AlertError, 'non confirmé'):
            tool.apply(plan(), protected, emit=lambda _: None)

    def test_gh_uses_argv_and_json_stdin_not_shell_interpolation(self):
        comment = "d'espaces ; $(touch /tmp/NEVER) et `commande`"
        payload = {'state': 'dismissed', 'dismissed_comment': comment}
        response = subprocess.CompletedProcess([], 0, stdout='{}', stderr='')
        with patch.object(tool.subprocess, 'run', return_value=response) as run:
            tool.gh_api(f'{tool.ROOT}/7', method='PATCH', payload=payload)
        args, kwargs = run.call_args
        self.assertNotIn(comment, args[0])
        self.assertEqual(json.loads(kwargs['input']), payload)
        self.assertNotIn('shell', kwargs)
        self.assertIn('--hostname', args[0])
        self.assertIn('github.com', args[0])
        self.assertEqual(args[0][-2:], ['--input', '-'])

    def test_gh_errors_are_explicit_and_never_retried(self):
        for result in [
            subprocess.CompletedProcess([], 1, stdout='', stderr='403 denied'),
            subprocess.CompletedProcess([], 0, stdout='not JSON', stderr=''),
        ]:
            with patch.object(tool.subprocess, 'run', return_value=result) as run:
                with self.assertRaises(tool.AlertError):
                    tool.gh_api(f'{tool.ROOT}/7')
                self.assertEqual(run.call_count, 1)

    def test_list_paginates_and_omits_fixed_alerts_without_auto_dismissal(self):
        calls = []

        def api(endpoint):
            calls.append(endpoint)
            if len(calls) == 1:
                return [alert(n) for n in range(1, 101)]
            fixed = alert(101)
            fixed['state'] = 'fixed'
            return [fixed, alert(102)]

        listed = tool.list_alerts(api)
        self.assertEqual(len(listed['alerts']), 101)
        self.assertTrue(all(row['state'] is None for row in listed['alerts']))
        self.assertIn('page=2', calls[1])

    def test_invalid_and_duplicate_json_or_missing_file_fail_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            for raw in [
                'invalid',
                '{"repository":"x","repository":"y"}',
                'a' * (tool.MAX_BYTES + 1),
            ]:
                path.write_text(raw)
                with self.subTest(raw=raw[:30]), self.assertRaises(tool.AlertError):
                    tool.load_plan(path)
            with self.assertRaises(tool.AlertError):
                tool.load_plan(None)
            with self.assertRaises(tool.AlertError):
                tool.load_plan(Path(directory) / 'absent')

    def test_make_passes_file_as_literal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'MUST_NOT_EXIST'
            command = [
                'make',
                '--no-print-directory',
                'security-plan',
                f'FILE=$(shell touch {marker})',
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertIn('Impossible de lire', result.stderr)

    def test_main_missing_file_is_a_clear_error(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch('sys.stderr', new_callable=io.StringIO) as error,
        ):
            self.assertEqual(tool.main(['apply']), 1)
        self.assertIn('FILE=', error.getvalue())
