import copy
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

from eures_beta.employers.offer_structuring import prepare, structure, validate_result
from eures_beta.integrations.albert import NoRedirect
from eures_beta.employers.offer_ingestion import ImportFailure
from eures_beta.occupations.catalog import rome_suggestions, suggestions

SOURCE = '''Société Démo recrute un électromécanicien pour la maintenance industrielle.
Contrat à durée indéterminée. Votre mission : réparer les palans.
Expérience minimum de 2 ans. Travail en hauteur.'''
RESULT = dict(
    occupation='électromécanicien',
    specialization='maintenance industrielle',
    companyName='Société Démo',
    city=None,
    contractType='PERMANENT_CONTRACT',
    contractEvidence='Contrat à durée indéterminée',
    missions=['réparer les palans', 'Travail en hauteur'],
    profile=['Expérience minimum de 2 ans'],
    experience='Expérience minimum de 2 ans',
    hours=None,
    salary=None,
)
ENABLED = dict(
    ALBERT_IMPORT_ENABLED=True,
    ALBERT_API_KEY='test-secret',
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)


class ValidationTests(SimpleTestCase):
    def test_qualified_title_can_suggest_the_explicit_broader_occupation(self):
        rows = suggestions('électricien industriel', 'fr')
        self.assertTrue(rows)
        self.assertIn('électricien', rows[0]['label'])

    def test_grounded_fields_and_missing_location(self):
        data = validate_result(RESULT, SOURCE)
        self.assertEqual(data['title'], 'électromécanicien — maintenance industrielle')
        self.assertEqual(data['city'], '')
        self.assertEqual(data['occupationQuery'], 'électromécanicien')
        self.assertEqual(len(data['description'].splitlines()), 2)
        self.assertNotIn('occupation', data)

    def test_invented_content_unknown_keys_and_malformed_types_are_rejected(self):
        for key, value in [
            ('companyName', ['Société Démo']),
            ('missions', ['Invented task']),
            ('contractEvidence', None),
            ('contractType', 'MAGIC_CONTRACT'),
            ('occupation', 4),
            ('rome', 'I1304'),
        ]:
            with self.subTest(key=key):
                bad = copy.deepcopy(RESULT)
                bad[key] = value
                with self.assertRaises(ImportFailure):
                    validate_result(bad, SOURCE)

    def test_unsupported_scalar_is_blank_without_discarding_verified_fields(self):
        value = {**RESULT, 'city': 'Paris', 'specialization': 'invented specialization'}
        data = validate_result(value, SOURCE)
        self.assertEqual(data['city'], '')
        self.assertEqual(data['title'], 'électromécanicien')
        self.assertEqual(data['companyName'], 'Société Démo')
        self.assertEqual(
            {x['field'] for x in data['extractionWarnings']}, {'city', 'specialization'}
        )
        self.assertEqual(data['extractionSource'], ' '.join(SOURCE.split()))

    @override_settings(**ENABLED)
    @patch('eures_beta.integrations.albert.build_opener')
    def test_bounded_request_and_valid_json(self, opener):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                'choices': [
                    {
                        'finish_reason': 'stop',
                        'message': {
                            'content': '```json\n' + json.dumps(RESULT) + '\n```'
                        },
                    }
                ]
            }
        ).encode()
        opener.return_value.open.return_value.__enter__.return_value = response
        self.assertEqual(structure(SOURCE)['city'], '')
        request = opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload['temperature'], 0)
        self.assertNotIn('test-secret', request.data.decode())
        self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 35)
        response.read.assert_called_once_with(100001)

    @override_settings(**ENABLED)
    @patch('eures_beta.integrations.albert.build_opener')
    def test_timeout_and_truncation_keep_manual_source_without_guessed_fields(
        self, opener
    ):
        opener.return_value.open.side_effect = TimeoutError('sensitive upstream error')
        data = prepare(SOURCE)
        self.assertEqual(data['description'], SOURCE)
        self.assertEqual(data['title'], '')
        self.assertEqual(data['extraction'], 'albert_fallback')
        self.assertNotIn('sensitive', json.dumps(data))

    @override_settings(ALBERT_IMPORT_ENABLED=False)
    @patch('eures_beta.integrations.albert.build_opener')
    def test_disabled_never_calls_network(self, opener):
        with self.assertRaises(ImportFailure):
            structure(SOURCE)
        opener.assert_not_called()

    @override_settings(**ENABLED)
    @patch('eures_beta.integrations.albert.build_opener')
    def test_all_environments_call_albert_even_with_email_enabled(self, opener):
        opener.return_value.open.side_effect = TimeoutError()
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                ),
            ):
                opener.reset_mock()
                self.assertEqual(prepare(SOURCE)['extraction'], 'albert_fallback')
                opener.assert_called_once()

    def test_redirects_never_forward_credentials(self):
        self.assertIsNone(
            NoRedirect().redirect_request(
                None, None, 302, '', {}, 'https://example.invalid'
            )
        )

    def test_rome_context_ranks_industrial_maintenance_without_esco_crosswalk(self):
        rows = rome_suggestions('électromécanicien', SOURCE)
        self.assertEqual(rows[0]['code'], 'I1304')
        self.assertEqual(rome_suggestions('I1304', 'ascenseurs')[0]['code'], 'I1304')


@override_settings(**ENABLED, DEMO_MODE=False, SHARED_DEMO=False)
class EndpointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        self.client.force_login(self.user)

    def test_import_is_available_outside_demo_in_all_environments(self):
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                ),
            ):
                response = self.client.get(
                    '/employer/pages/import-fr.html', REMOTE_ADDR='192.0.2.1'
                )
                self.assertContains(response, 'id="file-form"')
                self.assertEqual(
                    self.client.get(
                        '/api/imports/', REMOTE_ADDR='192.0.2.1'
                    ).status_code,
                    200,
                )

    @patch(
        'eures_beta.employers.offer_structuring.structure',
        return_value=validate_result(RESULT, SOURCE),
    )
    def test_saving_without_corrected_fields_does_not_persist_source_or_proofs(
        self, model
    ):
        from eures_beta.employers.models import JobOffer

        source = self.client.post(
            '/api/imports/source/',
            {'agreement': 'true', 'kind': 'manual', 'text': SOURCE},
        ).json()
        response = self.client.post(
            '/api/imports/',
            {
                'agreement': 'true',
                'kind': 'manual',
                'text': SOURCE,
                'sourceToken': source['token'],
                'contact': json.dumps(
                    {'name': 'Contact fictif', 'email': 'contact@example.invalid'}
                ),
            },
        )
        self.assertEqual(response.status_code, 201)
        data = JobOffer.objects.get().data
        self.assertEqual(data['companyName'], 'Société Démo')
        self.assertNotIn('extractionSource', data)
        self.assertNotIn('extractionEvidence', data)
        self.assertNotIn('pending_offer_source', self.client.session)

    @patch(
        'eures_beta.employers.offer_structuring.structure',
        return_value=validate_result(RESULT, SOURCE),
    )
    def test_manual_path_returns_grounded_data_without_storing_key(self, model):
        response = self.client.post(
            '/api/imports/source/',
            {'agreement': 'true', 'kind': 'manual', 'text': SOURCE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['city'], '')
        self.assertNotIn('test-secret', json.dumps(dict(self.client.session)))
        model.assert_called_once_with(SOURCE)

    @patch('eures_beta.employers.offer_structuring.structure')
    def test_other_roles_and_missing_agreement_never_send_content(self, model):
        self.assertEqual(
            self.client.post(
                '/api/imports/source/', {'kind': 'manual', 'text': SOURCE}
            ).status_code,
            400,
        )
        self.client.logout()
        self.assertEqual(
            self.client.post(
                '/api/imports/source/',
                {'agreement': 'true', 'kind': 'manual', 'text': SOURCE},
            ).status_code,
            403,
        )
        model.assert_not_called()

    def test_ai_disclosure_in_import_and_all_languages(self):
        for variant in ('import',):
            for language in ('fr', 'en', 'de'):
                page = self.client.get(f'/employer/pages/{variant}-{language}.html')
                self.assertContains(page, 'Albert')
                self.assertNotContains(page, 'test-secret')

    @patch('eures_beta.employers.employer_api.read_pdf')
    @patch(
        'eures_beta.employers.offer_structuring.structure',
        return_value=validate_result(RESULT, SOURCE),
    )
    def test_pdf_uses_complete_source_once_and_keeps_key_out_of_session(
        self, model, reader
    ):
        reader.return_value = {
            'description': 'Only a local section',
            '_sourceText': SOURCE,
        }
        response = self.client.post(
            '/api/imports/source/',
            {
                'agreement': 'true',
                'kind': 'pdf',
                'document': SimpleUploadedFile('fictional.pdf', b'%PDF-fictional'),
            },
        )
        self.assertEqual(response.status_code, 200)
        model.assert_called_once_with(SOURCE)
        self.assertTrue(reader.call_args.kwargs['include_text'])
        self.assertEqual(response.json()['data']['companyName'], 'Société Démo')
        self.assertNotIn('_sourceText', json.dumps(dict(self.client.session)))
        self.assertNotIn('test-secret', response.content.decode())

    @patch('eures_beta.employers.offer_structuring.structure')
    def test_csrf_is_required_before_any_external_call(self, model):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            '/api/imports/source/',
            {'agreement': 'true', 'kind': 'manual', 'text': SOURCE},
        )
        self.assertEqual(response.status_code, 403)
        model.assert_not_called()
