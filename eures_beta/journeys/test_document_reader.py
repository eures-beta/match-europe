import json
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .offer_ingestion import parse_pdf_text, read_pdf, ImportFailure


class DocumentFieldTests(SimpleTestCase):
    def test_missions_and_profile_keep_wrapped_text_and_requirement_strength(self):
        result = parse_pdf_text(
            'Conducteur H/F\nDescription du poste\nVous aurez pour mission de :- Livrer des marchandises.\nVous justifiez de 3 ans\nminimum dans la fonction et idéalement dans notre secteur.\nTitulaire du permis CE, une expérience grue est souhaitée.\nTravail du lundi au dimanche.\nComment postuler\nEnvoyez votre CV sur le site. Lisez nos autres annonces.'
        )
        self.assertIn('Livrer des marchandises', result['description'])
        self.assertIn('lundi au dimanche', result['description'])
        self.assertNotIn('3 ans', result['description'])
        self.assertIn('3 ans minimum', result['desiredProfile'])
        self.assertIn('idéalement', result['desiredProfile'])
        self.assertIn('souhaitée', result['desiredProfile'])
        self.assertNotIn('Envoyez', result['description'] + result['desiredProfile'])

    def test_continuation_after_pdf_metadata_keeps_tasks_without_calendar(self):
        result = parse_pdf_text(
            'Conducteur H/F\nDescription du poste\nLivrer des colis.\nDate limite de candidature\n6\nNOV. (NOVEMBRE)\n2026\nUtiliser un outil de navigation- Respecter les délais.\nVous justifiez de 3 ans minimum.'
        )
        self.assertIn('Utiliser un outil de navigation', result['description'])
        self.assertIn('Respecter les délais', result['description'])
        self.assertNotIn('NOV', result['description'])
        self.assertIn('3 ans minimum', result['desiredProfile'])

    def test_english_sections_preserve_hyphens_and_optional_skill(self):
        result = parse_pdf_text(
            'Growth Manager\nAbout us\nWe are a famous company.\nAbout the role\nDrive web growth.\nKey Responsibilities\nCross-Functional Collaboration: Work with designers.\nQualifications\n4+ years of product experience.\nFamiliarity with agile ceremonies is a plus.\nLocation\nRemote within 4 hours of CET.\nInterview Process\nTake a test.'
        )
        self.assertIn('Cross-Functional', result['description'])
        self.assertIn('Remote within 4 hours', result['description'])
        self.assertIn('4+ years', result['desiredProfile'])
        self.assertIn('is a plus', result['desiredProfile'])
        self.assertNotIn('famous', result['description'])
        self.assertNotIn(
            'Take a test', result['description'] + result['desiredProfile']
        )

    def test_german_sections_and_unchanged_language_level(self):
        result = parse_pdf_text(
            'Teststelle\nIhre Aufgaben\nSie liefern Waren.\nIhr Profil\nFührerschein CE erforderlich.\nDeutsch B1 wünschenswert.\nWir bieten\nFlexible Arbeitszeiten.'
        )
        self.assertIn('Sie liefern Waren', result['description'])
        self.assertIn('Flexible Arbeitszeiten', result['description'])
        self.assertIn('erforderlich', result['desiredProfile'])
        self.assertIn('B1 wünschenswert', result['desiredProfile'])

    def test_wrapped_header_and_conflicting_hours(self):
        result = parse_pdf_text(
            '20/10/2026 17:37 about:blank\nAgent test (m/f/x) - CDI,\n40h/semaine\nEntreprise fictive\nUpdated on: 01/01/2026\nJob location\nVille fictive\nDescription\nNous offrons un CDI de 20h/semaine.\nLanguages\nFrench (A1 - Beginner)'
        )
        self.assertEqual(result['companyName'], 'Entreprise fictive')
        self.assertEqual(result['city'], 'Ville fictive')
        self.assertEqual(result['clarifications']['hours'], '')
        self.assertEqual(
            result['extractionWarnings'][0]['values'], ['40h/semaine', '20h/semaine']
        )
        self.assertEqual(result['clarifications']['frenchLevel'], 'French : A1')

    def test_each_language_keeps_its_own_level(self):
        result = parse_pdf_text(
            'Poste fictif\nLanguages\nFrench (A1 - Beginner)\nEnglish: B2\nDeutsch C1'
        )
        self.assertEqual(
            result['clarifications']['frenchLevel'],
            'French : A1 ; English : B2 ; Deutsch : C1',
        )

    def test_unrelated_jobs_and_application_form_excluded(self):
        result = parse_pdf_text(
            'Agent test (h/f)\nPubliée le 01/01/2026\nEntreprise fictive\nVille du poste\nIndépendant / Freelance\nTemps plein\nTemps partiel\nNous ne proposons pas de salaire fixe.\nPOSTULEZ EN LIGNE\nNom\nEmail\nOffres similaires\nCDI\n60 - 75 EUR par heure'
        )
        self.assertEqual(result['contractType'], 'FREELANCE')
        self.assertEqual(result['city'], 'Ville du poste')
        self.assertNotIn('60', result['clarifications']['salary'])
        self.assertNotIn('Email', result['description'])

    def test_country_header_precise_workplace_and_permits(self):
        result = parse_pdf_text(
            'Conducteur H/F\nEntreprise fictive\nMise à jour le: 01/01/2026\nSituation géographique de l\x27emploi\nLuxembourg\nNotre site de Rodange au Luxembourg.\nPermis de conduire CE\nCACES grue auxiliaire\n3 ans\nminimum\n17.5 - 19 EUR par heure\nEmbauche directe'
        )
        self.assertEqual(result['city'], 'Rodange, Luxembourg')
        self.assertEqual(result['requirements']['permits'], ['CE', 'CACES'])
        self.assertEqual(result['contractType'], '')
        self.assertEqual(result['clarifications']['experience'], '3 ans minimum')

    def test_no_salary_or_language_level_invented(self):
        result = parse_pdf_text(
            'Test role\nAucun salaire indiqué\nLanguages\nFR, EN\nDescription in English.\nDébutant (- 1 an)\nPremière expérience (1 à 2 ans)'
        )
        self.assertEqual(result['clarifications']['salary'], '')
        self.assertEqual(result['clarifications']['frenchLevel'], '')
        self.assertEqual(result['clarifications']['experience'], '')

    @patch('eures_beta.journeys.offer_ingestion.subprocess.run')
    def test_image_reading_and_ocr_warning(self, run):
        run.return_value.stdout = json.dumps(
            {'text': 'Test role\nExample body', 'ocr': True}
        ).encode()
        result = read_pdf(SimpleUploadedFile('test.png', b'\x89PNG\r\n\x1a\nfiction'))
        self.assertEqual(result['extraction'], 'document_ocr')
        self.assertEqual(result['extractionWarnings'][-1]['field'], 'ocr')

    def test_forged_image_rejected(self):
        with self.assertRaises(ImportFailure):
            read_pdf(SimpleUploadedFile('test.png', b'%PDF-fiction'))


@patch.dict('os.environ', {'ME_EMPLOYER_LOCAL_API': '1'})
class MultipleImageTests(TestCase):
    @patch.dict('os.environ', {'ME_LOCAL_REVIEW_ONLY': '1'})
    @patch('eures_beta.journeys.employer_api.geocode')
    @patch('eures_beta.journeys.employer_api.aglae')
    def test_local_review_never_calls_external_services(self, api, geo):
        response = self.client.post(
            '/local-api/imports/',
            {
                'kind': 'manual',
                'agreement': 'true',
                'email': 'test@example.invalid',
                'contact': json.dumps(
                    {'name': 'Contact fictif', 'email': 'contact@example.invalid'}
                ),
                'text': 'Description fictive de test.',
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['stage'], 'review')
        api.assert_not_called()
        geo.assert_not_called()

    @patch('eures_beta.journeys.employer_api.read_pdf')
    def test_ordered_images_read_before_creating_draft(self, read):
        read.side_effect = [
            {
                'description': 'Agent test (h/f)\nPubliée le 01/01/2026\nEntreprise fictive\nVille fictive'
            },
            {'description': 'CDI\nTemps plein\nQualifications\nPermis B souhaité.'},
        ]
        response = self.client.post(
            '/local-api/imports/source/',
            {
                'kind': 'pdf',
                'agreement': 'true',
                'document': [
                    SimpleUploadedFile('1.png', b'one'),
                    SimpleUploadedFile('2.png', b'two'),
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = self.client.session['pending_offer_source']['data']
        self.assertEqual(data['contractType'], 'PERMANENT_CONTRACT')
        self.assertEqual(data['companyName'], 'Entreprise fictive')
        self.assertEqual(data['extraction'], 'document_ocr')
        self.assertIn('Permis B souhaité', data['desiredProfile'])

    @patch('eures_beta.journeys.employer_api.read_pdf')
    def test_multiple_pdfs_rejected_without_reading(self, read):
        response = self.client.post(
            '/local-api/imports/source/',
            {
                'kind': 'pdf',
                'agreement': 'true',
                'document': [
                    SimpleUploadedFile('1.pdf', b'one'),
                    SimpleUploadedFile('2.pdf', b'two'),
                ],
            },
        )
        self.assertEqual(response.status_code, 400)
        read.assert_not_called()
