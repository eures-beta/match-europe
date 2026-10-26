"""Keep the preview signal independent of GitHub's synthetic merge commit."""

from pathlib import Path
import unittest

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


class PreviewWorkflowTests(unittest.TestCase):
    def test_signal_runs_even_when_github_cannot_merge_the_pr(self):
        workflow = (WORKFLOWS / "preview-request.yml").read_text()
        self.assertIn("\n  pull_request_target:\n", workflow)
        self.assertNotIn("\n  pull_request:\n", workflow)
        # A target event must remain metadata-only, with no PR code or secrets.
        self.assertIn("permissions: {}", workflow)
        self.assertNotIn("uses:", workflow)
        self.assertNotIn("secrets.", workflow)
        commands = [line.strip() for line in workflow.splitlines() if "- run:" in line]
        self.assertEqual(
            commands,
            ["- run: echo 'Demande transmise au relais après cette exécution.'"],
        )
        self.assertIn("head.repo.full_name == github.repository", workflow)

    def test_relay_accepts_the_conflict_independent_signal(self):
        workflow = (WORKFLOWS / "preview-relay.yml").read_text()
        self.assertIn(
            "github.event.workflow_run.event == 'pull_request_target'", workflow
        )
        self.assertIn("head_repository.full_name == github.repository", workflow)
        self.assertIn("run.path !== '.github/workflows/preview-request.yml'", workflow)
        self.assertNotIn("actions/checkout", workflow)
