"""Protect real validation while avoiding cancelled push/PR duplicates."""

from pathlib import Path
import re
import unittest

WORKFLOWS = Path(__file__).resolve().parents[2] / '.github' / 'workflows'


class ReadinessWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (WORKFLOWS / 'ready-for-production-check.yml').read_text()

    def test_push_checks_every_internal_branch_even_without_a_mergeable_pr(self):
        self.assertRegex(
            self.workflow, r"push:\s*\n(?:\s*#[^\n]*\n)*\s*branches: \['\*\*'\]"
        )
        self.assertNotIn('pull_request_target:', self.workflow)

    def test_both_jobs_skip_internal_prs_but_accept_forks_and_dispatches(self):
        condition = (
            "github.event_name == 'push' || "
            "github.event_name == 'workflow_dispatch' || "
            'github.event.pull_request.head.repo.full_name != github.repository'
        )
        for job in ('e2e-memory', 'test'):
            with self.subTest(job=job):
                block = re.search(
                    rf'^  {job}:\n(.*?)(?=^  [a-z][\w-]*:|\Z)',
                    self.workflow,
                    re.MULTILINE | re.DOTALL,
                )[1]
                match = re.search(
                    r'^    if: >-\n((?:      .+\n)+)', block, re.MULTILINE
                )
                self.assertIsNotNone(
                    match, 'Internal PRs must not start duplicate jobs'
                )
                self.assertEqual(' '.join(match[1].split()), condition)
        self.assertIn('\n  pull_request:\n', self.workflow)
        self.assertIn('\n  workflow_dispatch:\n', self.workflow)

    def test_a_second_event_cannot_cancel_an_existing_validation(self):
        self.assertNotIn('\nconcurrency:', self.workflow)

    def test_quality_checks_validate_pushes_and_forks_without_cancelling_duplicates(
        self,
    ):
        condition = (
            "github.event_name == 'push' || "
            "github.event_name == 'workflow_dispatch' || "
            'github.event.pull_request.head.repo.full_name != github.repository'
        )
        for filename, job in (
            ('black.yml', 'black'),
            ('javascript.yml', 'prettier'),
            ('templates.yml', 'templates'),
        ):
            with self.subTest(workflow=filename):
                workflow = (WORKFLOWS / filename).read_text()
                self.assertNotIn('pull_request_target:', workflow)
                self.assertNotIn('\nconcurrency:', workflow)
                match = re.search(
                    rf'^  {job}:\n    if: >-\n((?:      .+\n)+)',
                    workflow,
                    re.MULTILINE,
                )
                self.assertIsNotNone(match)
                self.assertEqual(' '.join(match[1].split()), condition)

    def test_production_still_requires_a_successful_main_push_from_this_repository(
        self,
    ):
        relay = (WORKFLOWS / 'production-relay.yml').read_text()
        for guard in (
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.event == 'push'",
            "github.event.workflow_run.head_branch == 'main'",
            'github.event.workflow_run.head_repository.full_name == github.repository',
        ):
            self.assertIn(guard, relay)
        self.assertIn(
            "run.path !== '.github/workflows/ready-for-production-check.yml'", relay
        )
        self.assertNotIn('pull_request_target:', relay)
