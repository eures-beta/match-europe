import json
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .offer_ingestion import ImportFailure


class ReadingTests(SimpleTestCase):







    def test_pdf_offer_header_ignores_bullets_and_font_mapping(self):
        from .offer_ingestion import parse_pdf_text
        data=parse_pdf_text('●\n●\nVendeur H/F\nEntreprise Exɑmple\n•\n12345 Ville-Test\nContinuer pour postuler\nCDI, Temps plein\nDescription du poste\nMissions fictives.')
        self.assertEqual(data['title'],'Vendeur H/F')
        self.assertEqual(data['companyName'],'Entreprise Example')
        self.assertEqual(data['city'],'12345 Ville-Test')
        self.assertEqual(data['contractType'],'PERMANENT_CONTRACT')
        self.assertIn('Missions fictives.',data['description'])

    def test_pdf_does_not_invent_employer_or_use_body_address(self):
        from .offer_ingestion import parse_pdf_text
        data=parse_pdf_text('Poste fictif\nDescription du poste\nContact agence\n12345 Autre-Ville\nCDI ou CDD')
        self.assertEqual(data['companyName'],'')
        self.assertEqual(data['city'],'')
        self.assertEqual(data['contractType'],'')



