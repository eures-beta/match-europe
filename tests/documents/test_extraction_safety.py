"""Preserve source evidence and the bounds used to triage CodeQL alerts 4–12."""

import re
import subprocess
import sys
from unittest.mock import patch

from django.test import SimpleTestCase

from eures_beta.documents import document_fields
from eures_beta.employers.offer_ingestion import parse_pdf_text


class ExtractionSafetyTests(SimpleTestCase):
    def test_printed_url_pagination_preserves_the_original_suffix_grammar(self):
        for line in ('http://site/123/4', 'https://site/a7/8', 'about:blank ١/٢'):
            with self.subTest(line=line):
                self.assertTrue(document_fields.printed_url_page(line))
        for line in ('HTTP://site/1/2', 'https://site/abc/2', 'http://site/1/x', '1/2'):
            with self.subTest(line=line):
                self.assertFalse(document_fields.printed_url_page(line))

    def test_pagination_removed_without_discarding_a_numeric_job_description(self):
        result = parse_pdf_text('Agent H/F\nhttp://site/123/4\n123/4\n123/4 important')
        self.assertNotIn('http://site', result['description'])
        self.assertIn('123/4 important', result['description'])

    def test_commission_requires_the_percent_after_the_word(self):
        for line in ('Commission 10%', 'commissions variables 12 %', '% commission 5%'):
            self.assertTrue(document_fields.commission_percentage(line))
        for line in ('% commissions variables', 'commission variable', '10% salaire'):
            self.assertFalse(document_fields.commission_percentage(line))
        result = parse_pdf_text('Agent\nNo fixed salary\nCommissions variables 12 %')
        self.assertIn('Commissions variables 12 %', result['clarifications']['salary'])

    def test_experience_evidence_keeps_word_order_and_case(self):
        for line in (
            'EXPERIENCE is REQUIRED',
            'experience desirable, experience essential',
        ):
            self.assertTrue(document_fields.required_experience(line))
        for line in (
            'required, experience optional',
            'experience desirable',
            'expérience requise',
        ):
            self.assertFalse(document_fields.required_experience(line))
        result = parse_pdf_text('Agent\nEXPERIENCE is REQUIRED', split_sections=False)
        self.assertEqual(result['desiredProfile'], 'EXPERIENCE is REQUIRED')

    def test_repeated_failed_matches_finish_in_a_bounded_subprocess(self):
        # These formerly retried a wildcard from every candidate start. A generous
        # process timeout catches that regression without a millisecond benchmark.
        script = '''
from eures_beta.documents.document_fields import (
    printed_url_page, commission_percentage, required_experience,
)
assert not printed_url_page('http://' + '0' * 100000 + '!')
assert not commission_percentage('commissiona' * 10000)
assert not required_experience('experience' * 10000)
'''
        result = subprocess.run(
            [sys.executable, '-c', script], capture_output=True, text=True, timeout=3
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_long_heading_never_reaches_the_navigation_regex(self):
        original = re.search
        checked = []

        def search(pattern, value, *args, **kwargs):
            if pattern == r'Accueil|Jobs .*|offres.*emploi|chez .* à ':
                checked.append(value)
            return original(pattern, value, *args, **kwargs)

        with patch.object(document_fields.re, 'search', side_effect=search):
            parse_pdf_text('offres ' * 2000 + 'H/F\nAgent H/F')
        self.assertTrue(checked)
        self.assertTrue(all(len(value) < 125 for value in checked))

    def test_whitespace_is_normalized_before_field_and_paragraph_matching(self):
        source = (
            'Agent H/F\nEntreprise' + ' ' * 4000 + '• Équipe\nRemote\n'
            'Qualifications\nEnglish' + '\t ' * 2000 + ': B2\n'
            '3' + ' ' * 4000 + '+ years minimum\n'
            'Description\nLivrer des colis.' + ' ' * 1000 + '- Respecter les délais.'
        )
        with patch.object(
            document_fields,
            'document_sections',
            wraps=document_fields.document_sections,
        ) as sections:
            result = parse_pdf_text(source)
        lines = sections.call_args.args[0]
        self.assertTrue(
            all(line == line.strip() and '  ' not in line for line in lines)
        )
        self.assertEqual(result['companyName'], 'Entreprise')
        self.assertEqual(result['clarifications']['frenchLevel'], 'English : B2')
        self.assertIn('3 + years minimum', result['clarifications']['experience'])
        self.assertIn('Respecter les délais', result['description'])
