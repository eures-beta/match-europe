"""Exercise test imports before a deployment, using the installed environment."""

from pathlib import Path
import unittest


class TestCollectionTests(unittest.TestCase):
    def test_all_application_test_modules_can_be_imported(self):
        root = Path(__file__).resolve().parent.parent
        loader = unittest.TestLoader()
        suite = loader.discover(
            str(root / "eures_beta"), pattern="test*.py", top_level_dir=str(root)
        )
        self.assertGreater(suite.countTestCases(), 0)
        self.assertEqual(
            loader.errors,
            [],
            "Test dependencies are missing from the installed environment:\n"
            + "\n".join(loader.errors),
        )
