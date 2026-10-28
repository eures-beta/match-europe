import json
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from eures_beta.employers.models import EmployerImport
from eures_beta.employers.offer_ingestion import (
    parse_page,
    public_target,
    ImportFailure,
    read_url,
)


class ReadingTests(SimpleTestCase):
    @patch('eures_beta.employers.offer_ingestion.public_target')
    @patch('eures_beta.employers.offer_ingestion.fetch_public')
    def test_ft_dynamic_offer_uses_workplace_not_agency_address(self, fetch, target):
        sample = {
            'numeroOffre': 'Offre n° TEST123',
            'intituleOffre': 'Boucher test',
            'lieuTravail': 'Ville de travail (33)',
            'descriptif': 'Description de la seule offre testée.',
            'syntheseContrat': 'CDI - Contrat travail',
            'salaire': '12 EUR/h',
            'etablissement': {
                'libelleEnseigne': 'Agence fictive',
                'codePostalCommune': 'Autre ville',
            },
            'experienceProfil': {'experience': '1 An(s)'},
        }
        fetch.return_value = (
            json.dumps(sample),
            'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123',
        )
        data, _ = read_url(
            'https://candidat.francetravail.fr/offres/recherche/detail/TEST123'
        )
        self.assertEqual(data['title'], 'Boucher test')
        self.assertEqual(data['city'], 'Ville de travail (33), France')
        self.assertNotIn('Autre ville', data['city'])
        self.assertEqual(data['clarifications']['salary'], '12 EUR/h')
        self.assertEqual(data['contractType'], 'PERMANENT_CONTRACT')

    @patch('eures_beta.employers.offer_ingestion.public_target')
    @patch('eures_beta.employers.offer_ingestion.fetch_public')
    def test_ft_hours_use_workplace_conditions_when_summary_unavailable(
        self, fetch, target
    ):
        sample = {
            'numeroOffre': 'TEST123',
            'intituleOffre': 'Poste fictif',
            'lieuTravail': 'Ville test',
            'descriptif': 'Description fictive.',
            'syntheseHoraire': 'Non disponible',
            'descriptionEntreprise': 'Agence ouverte de 8h à 18h',
            'conditionTravailPoste': {
                'listeLibelleTypeHoraire': [
                    '35H/semaine',
                    'Travail en journée',
                    ' Travail le samedi',
                ],
                'listeLibelleConditionExerciceHoraire': None,
            },
        }
        fetch.return_value = (
            json.dumps(sample),
            'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123',
        )
        data, _ = read_url(
            'https://candidat.francetravail.fr/offres/recherche/detail/TEST123'
        )
        self.assertEqual(
            data['clarifications']['hours'],
            '35H/semaine ; Travail en journée ; Travail le samedi',
        )
        self.assertNotIn('8h', data['clarifications']['hours'])
        self.assertEqual(data['requirements']['workConditions'], ['weekend'])
        sample['syntheseHoraire'] = '35H/semaine'
        fetch.return_value = (
            json.dumps(sample),
            'https://candidat.francetravail.fr/api-descriptifoffre/offre/TEST123',
        )
        self.assertEqual(
            read_url(
                'https://candidat.francetravail.fr/offres/recherche/detail/TEST123'
            )[0]['clarifications']['hours'].count('35H/semaine'),
            1,
        )

    def test_requirements_validation_and_backward_compatible_defaults(self):
        from eures_beta.employers.employer_api import clean_data

        data = clean_data(
            {
                'requirements': {
                    'workConditions': ['weekend', 'physical'],
                    'permitRequired': 'yes',
                    'permits': ['B', 'other'],
                    'permitOther': 'Autorisation fictive',
                    'arrivalAids': ['housing'],
                }
            }
        )
        self.assertEqual(data['requirements']['permits'], ['B', 'other'])
        self.assertEqual(data['requirements']['arrivalAids'], ['housing'])
        self.assertEqual(clean_data({})['requirements']['workConditions'], [])
        for req in (
            {'workConditions': ['none', 'night']},
            {'permits': ['invalid']},
            {'arrivalAids': 'housing'},
            {'permitRequired': 'invalid'},
        ):
            with self.assertRaises(ImportFailure):
                clean_data({'requirements': req})
        cleared = clean_data(
            {
                'requirements': {
                    'permitRequired': 'no',
                    'permits': ['B'],
                    'permitOther': 'Hidden value',
                }
            }
        )
        self.assertEqual(cleared['requirements']['permits'], [])
        self.assertEqual(cleared['requirements']['permitOther'], '')

    @patch('eures_beta.employers.offer_ingestion.fetch_public')
    def test_ft_search_page_is_rejected_before_fetch(self, fetch):
        with self.assertRaises(ImportFailure) as caught:
            read_url('https://candidat.francetravail.fr/offres/emploi/boucher/s11m12')
        self.assertEqual(caught.exception.code, 'individual_offer_required')
        fetch.assert_not_called()

    def test_jobposting_fields_and_missing_information(self):
        page = (
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    '@type': 'JobPosting',
                    'title': 'Test job',
                    'description': 'A sample role for a fictional company. FULL_TIME',
                    'hiringOrganization': {'name': 'Example company'},
                    'employmentType': 'FULL_TIME',
                    'jobLocation': {
                        'address': {
                            'addressLocality': 'Testville',
                            'addressCountry': 'FR',
                        }
                    },
                }
            )
            + '</script>'
        )
        data = parse_page(page)
        self.assertEqual(data['title'], 'Test job')
        self.assertEqual(data['companyName'], 'Example company')
        self.assertEqual(data['contractType'], '')
        self.assertEqual(data['clarifications']['salary'], '')
        self.assertEqual(data['questions'], [])

    @patch('eures_beta.employers.offer_ingestion.socket.getaddrinfo')
    def test_mixed_or_private_dns_answers_rejected(self, resolve):
        resolve.return_value = [
            (2, 1, 6, '', ('93.184.216.34', 443)),
            (2, 1, 6, '', ('127.0.0.1', 443)),
        ]
        with self.assertRaises(ImportFailure):
            public_target('https://public.example.org/job')

    def test_credentials_ports_and_protocol_rejected(self):
        for url in [
            'http://example.org',
            'https://a:b@example.org',
            'https://example.org:8080',
            'file:///etc/passwd',
        ]:
            with self.assertRaises(ImportFailure):
                public_target(url)

    def test_pdf_offer_header_ignores_bullets_and_font_mapping(self):
        from eures_beta.employers.offer_ingestion import parse_pdf_text

        data = parse_pdf_text(
            '●\n●\nVendeur H/F\nEntreprise Exɑmple\n•\n12345 Ville-Test\nContinuer pour postuler\nCDI, Temps plein\nDescription du poste\nMissions fictives.'
        )
        self.assertEqual(data['title'], 'Vendeur H/F')
        self.assertEqual(data['companyName'], 'Entreprise Example')
        self.assertEqual(data['city'], '12345 Ville-Test')
        self.assertEqual(data['contractType'], 'PERMANENT_CONTRACT')
        self.assertIn('Missions fictives.', data['description'])

    def test_pdf_does_not_invent_employer_or_use_body_address(self):
        from eures_beta.employers.offer_ingestion import parse_pdf_text

        data = parse_pdf_text(
            'Poste fictif\nDescription du poste\nContact agence\n12345 Autre-Ville\nCDI ou CDD'
        )
        self.assertEqual(data['companyName'], '')
        self.assertEqual(data['city'], '')
        self.assertEqual(data['contractType'], '')

    def test_hidden_scripts_not_description(self):
        d = parse_page(
            '<title>Example offer</title><script>secret_script()</script><article>'
            + ('Useful job description. ' * 10)
            + '</article>'
        )
        self.assertNotIn('secret_script', d['description'])


@patch.dict('os.environ', {'ME_EMPLOYER_DEV_ACCESS': '1'})
class ImportFlowTests(TestCase):
    def create(self):
        return self.client.post(
            '/api/imports/',
            {
                'kind': 'manual',
                'text': 'A useful fictional job description.',
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'contact@example.invalid'}
                ),
                'email': 'fiction@example.invalid',
                'agreement': 'true',
            },
        )

    def payload(self, result):
        data = result['data']
        data.update(
            title='Example role',
            companyName='Example company',
            city='Testville',
            contractType='PERMANENT_CONTRACT',
        )
        return data

    def update(self, result, action='save', **kwargs):
        return self.client.post(
            '/api/imports/' + result['id'] + '/',
            json.dumps(
                {
                    'action': action,
                    'revision': result['revision'],
                    'data': self.payload(result),
                    **kwargs,
                }
            ),
            content_type='application/json',
        )

    def test_draft_stored_and_owned_by_session(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        obj = response.json()
        self.assertTrue(EmployerImport.objects.filter(pk=obj['id']).exists())
        self.assertEqual(
            self.client.get('/api/imports/' + obj['id'] + '/').status_code, 200
        )
        self.assertEqual(
            Client().get('/api/imports/' + obj['id'] + '/').status_code, 404
        )

    @patch('eures_beta.employers.employer_api.aglae')
    @patch('eures_beta.employers.employer_api.geocode')
    @patch(
        'eures_beta.employers.employer_api.read_pdf',
        return_value={
            'title': 'Original title',
            'description': 'Fictional PDF text',
            'extractionWarnings': [],
        },
    )
    def test_review_before_contact_preserves_corrections(self, read, geo, aglae):
        first = self.client.post(
            '/api/imports/source/',
            {
                'kind': 'pdf',
                'agreement': 'true',
                'document': SimpleUploadedFile('offer.pdf', b'%PDF-test'),
            },
        )
        self.assertEqual(first.status_code, 200)
        summary = first.json()
        self.assertEqual(summary['stage'], 'review')
        self.assertEqual(summary['data']['title'], 'Original title')
        self.assertNotIn('id', summary)
        self.assertEqual(EmployerImport.objects.count(), 0)
        payload = {
            'kind': 'pdf',
            'agreement': 'true',
            'sourceToken': summary['token'],
            'email': 'fiction@example.invalid',
            'contact': json.dumps(
                {'name': 'Fictional contact', 'email': 'contact@example.invalid'}
            ),
            'data': json.dumps({**summary['data'], 'title': 'Corrected title'}),
        }
        with patch.dict('os.environ', {'ME_LOCAL_REVIEW_ONLY': '1'}):
            created = self.client.post('/api/imports/', payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['data']['title'], 'Corrected title')
        self.assertEqual(created.json()['data']['description'], 'Fictional PDF text')
        read.assert_called_once()
        geo.assert_not_called()
        aglae.assert_not_called()
        self.assertEqual(self.client.post('/api/imports/', payload).status_code, 400)

    def test_manual_summary_does_not_require_contact_or_create_import(self):
        result = self.client.post(
            '/api/imports/source/',
            {'kind': 'manual', 'agreement': 'true', 'text': 'Fictional manual offer.'},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            result.json()['data']['description'], 'Fictional manual offer.'
        )
        self.assertEqual(EmployerImport.objects.count(), 0)
        self.assertEqual(
            self.client.post(
                '/api/imports/source/',
                {'kind': 'manual', 'text': 'Fictional offer.'},
            ).status_code,
            400,
        )

    def test_requirements_survive_save_and_resume(self):
        created = self.create().json()
        req = {
            'workConditions': ['weekend', 'standing'],
            'permitRequired': 'yes',
            'permits': ['B'],
            'permitOther': '',
            'arrivalAids': ['housing', 'admin'],
            'aidOther': '',
        }
        created['data']['requirements'] = req
        response = self.update(created)
        self.assertEqual(response.status_code, 200)
        resumed = self.client.get('/api/imports/' + created['id'] + '/').json()
        self.assertEqual(resumed['data']['requirements'], req)
        self.assertEqual(
            EmployerImport.objects.get(pk=created['id']).data['requirements'], req
        )

    def test_consent_required_before_reading(self):
        with patch('eures_beta.employers.offer_ingestion.fetch_public') as fetch:
            r = self.client.post(
                '/api/imports/',
                {
                    'kind': 'url',
                    'url': 'https://example.org/job',
                    'contact': json.dumps(
                        {
                            'name': 'Fictional contact',
                            'email': 'contact@example.invalid',
                        }
                    ),
                    'email': 'fiction@example.invalid',
                },
            )
            self.assertEqual(r.status_code, 400)
            fetch.assert_not_called()

    def test_real_parser_not_saved_example(self):
        html = (
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    '@type': 'JobPosting',
                    'title': 'Different job',
                    'description': 'Different fictional job description',
                    'hiringOrganization': {'name': 'Different company'},
                }
            )
            + '</script>'
        )
        with patch(
            'eures_beta.employers.offer_ingestion.fetch_public',
            return_value=(html, 'https://example.org/different'),
        ):
            first = self.client.post(
                '/api/imports/source/',
                {'url': 'https://example.org/different', 'agreement': 'true'},
            )
            self.assertEqual(first.status_code, 200)
            r = self.client.post(
                '/api/imports/',
                {
                    'kind': 'url',
                    'url': 'https://example.org/different',
                    'contact': json.dumps(
                        {
                            'name': 'Fictional contact',
                            'email': 'contact@example.invalid',
                        }
                    ),
                    'email': 'fiction@example.invalid',
                    'agreement': 'true',
                    'sourceToken': first.json()['token'],
                },
            )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['data']['title'], 'Different job')

    @patch(
        'eures_beta.employers.offer_ingestion.fetch_public',
        side_effect=ImportFailure('unreadable_url'),
    )
    def test_blocked_source_fails_before_email(self, fetch):
        r = self.client.post(
            '/api/imports/source/',
            {'url': 'https://example.org/blocked', 'agreement': 'true'},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(EmployerImport.objects.count(), 0)

    def test_preflight_cannot_be_reused_for_another_source(self):
        session = self.client.session
        session['pending_offer_source'] = {
            'url': 'https://example.org/one',
            'token': 'test',
            'at': 9999999999,
            'data': {},
        }
        session.save()
        r = self.client.post(
            '/api/imports/',
            {
                'kind': 'url',
                'url': 'https://example.org/two',
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'contact@example.invalid'}
                ),
                'email': 'fiction@example.invalid',
                'agreement': 'true',
                'sourceToken': 'test',
            },
        )
        self.assertEqual(r.status_code, 400)

    @patch(
        'eures_beta.employers.employer_api.read_pdf',
        return_value={'description': 'Fictional PDF text'},
    )
    def test_pdf_read_before_email_and_reused_once(self, read):
        first = self.client.post(
            '/api/imports/source/',
            {
                'kind': 'pdf',
                'agreement': 'true',
                'document': SimpleUploadedFile('offer.pdf', b'%PDF-test'),
            },
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(EmployerImport.objects.count(), 0)
        payload = {
            'kind': 'pdf',
            'agreement': 'true',
            'contact': json.dumps(
                {'name': 'Fictional contact', 'email': 'contact@example.invalid'}
            ),
            'email': 'fiction@example.invalid',
            'sourceToken': first.json()['token'],
        }
        self.assertEqual(Client().post('/api/imports/', payload).status_code, 400)
        created = self.client.post('/api/imports/', payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['data']['description'], 'Fictional PDF text')
        self.assertEqual(self.client.post('/api/imports/', payload).status_code, 400)
        read.assert_called_once()

    @patch(
        'eures_beta.employers.employer_api.read_pdf',
        side_effect=ImportFailure('unreadable'),
    )
    def test_unreadable_pdf_fails_before_email(self, read):
        payload = {
            'kind': 'pdf',
            'document': SimpleUploadedFile('offer.pdf', b'%PDF-test'),
        }
        self.assertEqual(
            self.client.post('/api/imports/source/', payload).status_code, 400
        )
        read.assert_not_called()
        payload.update(
            agreement='true', document=SimpleUploadedFile('offer.pdf', b'%PDF-test')
        )
        response = self.client.post('/api/imports/source/', payload)
        self.assertEqual(response.json()['error'], 'unreadable')
        self.assertEqual(EmployerImport.objects.count(), 0)

    @patch(
        'eures_beta.employers.employer_api.read_pdf',
        return_value={'description': 'Fictional PDF text'},
    )
    def test_expired_pdf_preflight_is_rejected(self, read):
        first = self.client.post(
            '/api/imports/source/',
            {
                'kind': 'pdf',
                'agreement': 'true',
                'document': SimpleUploadedFile('offer.pdf', b'%PDF-test'),
            },
        )
        session = self.client.session
        pending = session['pending_offer_source']
        pending['at'] = 0
        session['pending_offer_source'] = pending
        session.save()
        self.assertEqual(
            self.client.post(
                '/api/imports/',
                {
                    'kind': 'pdf',
                    'agreement': 'true',
                    'contact': json.dumps(
                        {
                            'name': 'Fictional contact',
                            'email': 'contact@example.invalid',
                        }
                    ),
                    'email': 'fiction@example.invalid',
                    'sourceToken': first.json()['token'],
                },
            ).status_code,
            400,
        )

    def test_persistent_edit_and_revision(self):
        obj = self.create().json()
        r = self.update(obj)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            self.client.get('/api/imports/' + obj['id'] + '/').json()['data']['title'],
            'Example role',
        )
        self.assertEqual(self.update(obj).status_code, 409)

    @patch('eures_beta.employers.employer_api.aglae')
    def test_no_api_call_without_validation_or_location(self, api):
        obj = self.create().json()
        self.assertEqual(self.update(obj).status_code, 200)
        obj = self.client.get('/api/imports/' + obj['id'] + '/').json()
        self.assertEqual(self.update(obj, 'validate', confirmed=True).status_code, 400)
        api.assert_not_called()

    @patch('eures_beta.employers.employer_api.aglae')
    @patch(
        'eures_beta.employers.employer_api.geocode',
        return_value={
            'latitude': 48.0,
            'longitude': 2.0,
            'query': 'Testville',
            'label': 'Testville',
        },
    )
    def test_validation_sends_only_inactive_offer_and_questions(self, geo, api):
        obj = self.create().json()
        EmployerImport.objects.filter(pk=obj['id']).update(
            initial_sent_at=timezone.now()
        )
        obj['data']['questions'] = [{'question': 'Available when?', 'mandatory': True}]
        api.side_effect = [
            {},
            {},
            {'id': obj['id'], 'active': False, 'title': 'Example role'},
        ]
        r = self.update(obj, 'validate', confirmed=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['synced'])
        paths = [c.args[1] for c in api.call_args_list]
        self.assertFalse(any('qualification' in p or 'leads' in p for p in paths))
        payload = api.call_args_list[0].args[2]
        self.assertFalse(payload['jobPostings'][0]['active'])
        self.assertNotIn('fiction@example.invalid', json.dumps(payload))
        self.assertFalse(
            api.call_args_list[1].args[2]['specificPrerequisites'][0]['isMandatory']
        )

    @patch(
        'eures_beta.employers.employer_api.aglae',
        side_effect=ImportFailure('sandbox_error'),
    )
    @patch(
        'eures_beta.employers.employer_api.geocode',
        return_value={
            'latitude': 48.0,
            'longitude': 2.0,
            'query': 'Testville',
            'label': 'Testville',
        },
    )
    def test_failed_sync_keeps_corrections_without_success(self, geo, api):
        obj = self.create().json()
        obj = self.update(obj, 'locate').json()
        EmployerImport.objects.filter(pk=obj['id']).update(
            initial_sent_at=timezone.now()
        )
        r = self.update(obj, 'validate', confirmed=True, locationConfirmed=True)
        self.assertEqual(r.status_code, 502)
        row = EmployerImport.objects.get(pk=obj['id'])
        self.assertEqual(row.data['title'], 'Example role')
        self.assertIsNone(row.synced_at)

    @patch(
        'eures_beta.employers.employer_api.geocode',
        return_value={
            'latitude': 48.0,
            'longitude': 2.0,
            'query': 'Testville',
            'label': 'Testville',
        },
    )
    @patch('eures_beta.employers.employer_api.aglae')
    def test_initial_send_and_readback_precede_review(self, api, geo):
        obj = self.create().json()
        self.assertEqual(obj['stage'], 'prepare')
        api.assert_not_called()
        api.side_effect = [
            {},
            {
                'id': obj['id'],
                'active': False,
                'title': 'Returned by sandbox',
                'companyName': 'Example company',
                'description': 'Actual returned description',
            },
        ]
        r = self.update(obj, 'prepare')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['stage'], 'review')
        self.assertEqual(r.json()['data']['title'], 'Returned by sandbox')
        self.assertFalse(r.json()['synced'])
        self.assertEqual([c.args[0] for c in api.call_args_list], ['POST', 'GET'])
        self.assertFalse(api.call_args_list[0].args[2]['jobPostings'][0]['active'])

    def test_remote_client_and_missing_csrf_rejected(self):
        self.assertEqual(
            self.client.get('/api/imports/', REMOTE_ADDR='192.0.2.1').status_code,
            404,
        )
        self.assertEqual(
            Client(enforce_csrf_checks=True).post('/api/imports/', {}).status_code,
            403,
        )

    def test_pdf_reader_receives_actual_document(self):
        with patch('eures_beta.employers.offer_ingestion.subprocess.run') as run:
            run.return_value.stdout = json.dumps(
                {
                    'text': 'Example extracted title\nAn actual extracted fictional document.'
                }
            ).encode()
            first = self.client.post(
                '/api/imports/source/',
                {
                    'kind': 'pdf',
                    'document': SimpleUploadedFile('test.pdf', b'%PDF-1.4\nfiction'),
                    'agreement': 'true',
                },
            )
            self.assertEqual(first.status_code, 200)
            r = self.client.post(
                '/api/imports/',
                {
                    'kind': 'pdf',
                    'sourceToken': first.json()['token'],
                    'contact': json.dumps(
                        {
                            'name': 'Fictional contact',
                            'email': 'contact@example.invalid',
                        }
                    ),
                    'email': 'fiction@example.invalid',
                    'agreement': 'true',
                },
            )
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.json()['data']['title'], 'Example extracted title')
