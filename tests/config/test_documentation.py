from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from config.documentation import Budget, check_documents


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def test_required_document_missing_fails_closed(self):
        errors, _ = check_documents(self.root, {'HANDOFF.md': Budget(50, 5)})
        self.assertEqual(len(errors), 1)
        self.assertIn('HANDOFF.md', errors[0])

    def test_utf8_bytes_and_exact_boundary_are_counted(self):
        self.write('AGENTS.md', 'é\n')
        errors, _ = check_documents(self.root, {'AGENTS.md': Budget(3, 1)})
        self.assertEqual(errors, [])
        errors, _ = check_documents(self.root, {'AGENTS.md': Budget(2, 1)})
        self.assertEqual(len(errors), 1)
        self.assertIn('3/2 octets', errors[0])

    def test_many_short_lines_fail_independently_of_byte_limit(self):
        self.write('HANDOFF.md', 'a\nb\nc\n')
        errors, _ = check_documents(self.root, {'HANDOFF.md': Budget(1000, 2)})
        self.assertEqual(len(errors), 1)
        self.assertIn('3/2 lignes', errors[0])

    def test_new_nested_rules_and_skills_are_automatically_checked(self):
        self.write('domain/AGENTS.md', 'a' * 4097)
        self.write('.agents/skills/example/SKILL.md', 'b' * 4097)
        errors, _ = check_documents(self.root, {})
        self.assertEqual(len(errors), 2)
        self.assertTrue(any('domain/AGENTS.md' in error for error in errors))
        self.assertTrue(any('SKILL.md' in error for error in errors))

    def test_chain_budget_counts_ancestors_and_override_but_not_siblings(self):
        self.write('AGENTS.md', 'a' * 10000)
        self.write('one/AGENTS.md', 'b' * 4000)
        self.write('one/two/AGENTS.md', 'c' * 4000)
        self.write('one/two/AGENTS.override.md', 'd' * 4000)
        self.write('sibling/AGENTS.md', 'e' * 4000)
        errors, _ = check_documents(self.root, {'AGENTS.md': Budget(10240, 180)})
        self.assertEqual(len(errors), 1)
        self.assertIn('one/two: chaîne AGENTS 22000/20480', errors[0])

    def test_generated_and_installed_files_are_ignored_but_long_guides_are_allowed(
        self,
    ):
        for prefix in ('.venv', '.venv-quality', 'node_modules', '.git', '.runtime'):
            self.write(prefix + '/AGENTS.md', 'a' * 50000)
        self.write('docs/long-technical-guide.md', 'b' * 50000)
        self.assertEqual(check_documents(self.root, {}), ([], []))

    def test_invalid_utf8_is_a_controlled_failure(self):
        self.write('AGENTS.md', 'valid').write_bytes(b'\xff')
        errors, _ = check_documents(self.root, {})
        self.assertEqual(len(errors), 1)
        self.assertIn('UTF-8', errors[0])
