from pathlib import Path
import tempfile
from django.test import SimpleTestCase

from .translation_check import incomplete_entries


class CatalogCompletenessTests(SimpleTestCase):
    def test_untranslated_and_fuzzy_messages_are_reported_but_header_is_not(self):
        header = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'example.po'
            path.write_text(header + 'msgid "Complete"\nmsgstr "Complet"\n')
            self.assertEqual(incomplete_entries(path), [])
            path.write_text(
                header
                + 'msgid "Missing"\nmsgstr ""\n\n#, fuzzy\nmsgid "Unreviewed"\nmsgstr "À relire"\n'
            )
            issues = incomplete_entries(path)
            self.assertEqual(len(issues), 2)
            self.assertIn('Missing', '\n'.join(issues))
            self.assertIn('Unreviewed', '\n'.join(issues))
