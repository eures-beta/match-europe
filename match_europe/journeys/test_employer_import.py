import json
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .offer_ingestion import parse_page, public_target, ImportFailure, read_url


class ReadingTests(SimpleTestCase):
    @patch('journeys.offer_ingestion.public_target')
    @patch('journeys.offer_ingestion.fetch_public')
    def test_ft_dynamic_offer_uses_workplace_not_agency_address(self,fetch,target):
        sample={'numeroOffre':'Offre n° TEST123','intituleOffre':'Boucher test','lieuTravail':'Ville de travail (33)',
                'descriptif':'Description de la seule offre testée.','syntheseContrat':'CDI - Contrat travail','salaire':'12 EUR/h',
                'etablissement':{'libelleEnseigne':'Agence fictive','codePostalCommune':'Autre ville'},'experienceProfil':{'experience':'1 An(s)'}}
        fetch.return_value=(json.dumps(sample),'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123')
        data,_=read_url('https://candidat.francetravail.fr/offres/recherche/detail/TEST123')
        self.assertEqual(data['title'],'Boucher test');self.assertEqual(data['city'],'Ville de travail (33), France')
        self.assertNotIn('Autre ville',data['city']);self.assertEqual(data['clarifications']['salary'],'12 EUR/h')
        self.assertEqual(data['contractType'],'PERMANENT_CONTRACT')

    @patch('journeys.offer_ingestion.public_target')
    @patch('journeys.offer_ingestion.fetch_public')
    def test_ft_hours_use_workplace_conditions_when_summary_unavailable(self,fetch,target):
        sample={'numeroOffre':'TEST123','intituleOffre':'Poste fictif','lieuTravail':'Ville test',
                'descriptif':'Description fictive.','syntheseHoraire':'Non disponible',
                'descriptionEntreprise':'Agence ouverte de 8h à 18h',
                'conditionTravailPoste':{'listeLibelleTypeHoraire':['35H/semaine','Travail en journée',' Travail le samedi'],
                                        'listeLibelleConditionExerciceHoraire':None}}
        fetch.return_value=(json.dumps(sample),'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123')
        data,_=read_url('https://candidat.francetravail.fr/offres/recherche/detail/TEST123')
        self.assertEqual(data['clarifications']['hours'],'35H/semaine ; Travail en journée ; Travail le samedi')
        self.assertNotIn('8h',data['clarifications']['hours'])
        self.assertEqual(data['requirements']['workConditions'],['weekend'])
        sample['syntheseHoraire']='35H/semaine'
        fetch.return_value=(json.dumps(sample),'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123')
        self.assertEqual(read_url('https://candidat.francetravail.fr/offres/recherche/detail/TEST123')[0]['clarifications']['hours'].count('35H/semaine'),1)


    @patch('journeys.offer_ingestion.fetch_public')
    def test_ft_search_page_is_rejected_before_fetch(self,fetch):
        with self.assertRaises(ImportFailure) as caught:
            read_url('https://candidat.francetravail.fr/offres/emploi/boucher/s11m12')
        self.assertEqual(caught.exception.code,'individual_offer_required')
        fetch.assert_not_called()

    def test_jobposting_fields_and_missing_information(self):
        page='<script type="application/ld+json">'+json.dumps({'@type':'JobPosting','title':'Test job','description':'A sample role for a fictional company. FULL_TIME','hiringOrganization':{'name':'Example company'},'employmentType':'FULL_TIME','jobLocation':{'address':{'addressLocality':'Testville','addressCountry':'FR'}}})+'</script>'
        data=parse_page(page)
        self.assertEqual(data['title'],'Test job')
        self.assertEqual(data['companyName'],'Example company')
        self.assertEqual(data['contractType'],'')
        self.assertEqual(data['clarifications']['salary'],'')
        self.assertEqual(data['questions'],[])

    @patch('journeys.offer_ingestion.socket.getaddrinfo')
    def test_mixed_or_private_dns_answers_rejected(self,resolve):
        resolve.return_value=[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('127.0.0.1',443))]
        with self.assertRaises(ImportFailure): public_target('https://public.example.org/job')

    def test_credentials_ports_and_protocol_rejected(self):
        for url in ['http://example.org','https://a:b@example.org','https://example.org:8080','file:///etc/passwd']:
            with self.assertRaises(ImportFailure):public_target(url)

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

    def test_hidden_scripts_not_description(self):
        d=parse_page('<title>Example offer</title><script>secret_script()</script><article>'+('Useful job description. '*10)+'</article>')
        self.assertNotIn('secret_script',d['description'])


