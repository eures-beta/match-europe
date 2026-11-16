"""Exercise the actual djLint CSS policy, including its narrow exceptions.

Run by format-html-check with the quality environment, not a runtime dependency.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
WEB = 'eures_beta/templates/example.html'
CATALOGUE = 'eures_beta/templates/design_system.html'
EMAIL = 'eures_beta/invitations/templates/invitations/emails/candidate/example.html'


@unittest.skipUnless(
    importlib.util.find_spec('djlint'), 'Runs in the quality environment'
)
class TemplateStylePolicyTests(unittest.TestCase):
    def lint(self, body, relative=WEB):
        with TemporaryDirectory() as directory:
            path = Path(directory) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
            return subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'djlint',
                    str(path),
                    '--lint',
                    '--configuration',
                    str(ROOT / '.djlint-css.json'),
                    '--rules',
                    str(ROOT / '.djlint_rules.yaml'),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_web_stylesheet_links_and_classes_are_allowed(self):
        result = self.lint(
            '{% load static %}<link rel="stylesheet" href="{% static \'example.css\' %}">'
            '<p class="example">A page</p>'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_style_blocks_are_rejected(self):
        for markup in (
            '<style>.example { color: red; }</style>',
            '<STYLE media="screen">p{}</STYLE>',
        ):
            with self.subTest(markup=markup):
                result = self.lint(markup)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('C901', result.stdout)

    def test_inline_styles_after_django_conditions_are_rejected(self):
        result = self.lint(
            '<div {% if n > 5 %}id="example"{% endif %} style="color:red">Text</div>'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('H021', result.stdout)

    def test_email_styles_remain_allowed(self):
        result = self.lint(
            '<style>p{color:red}</style><p style="color:red">An email</p>', EMAIL
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_catalogue_can_demonstrate_dynamic_tokens(self):
        result = self.lint(
            '<div style="background:var({{ colour.name }})"></div>', CATALOGUE
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_catalogue_cannot_add_style_blocks(self):
        result = self.lint('<style>p{color:red}</style>', CATALOGUE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('C901', result.stdout)

    def test_similarly_named_web_pages_are_not_exempt(self):
        for path in (
            'eures_beta/templates/other_design_system.html',
            'eures_beta/templates/emails/example.html',
        ):
            with self.subTest(path=path):
                result = self.lint('<p style="color:red">A page</p>', path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('H021', result.stdout)

    def test_comments_and_script_text_are_not_mistaken_for_real_styles(self):
        result = self.lint(
            '<!-- <style>p{}</style> -->'
            '<script>const sample = "<style>p{}</style>";</script>'
            '<div data-example="<style>">Example</div>'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
