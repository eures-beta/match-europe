"""Fictional examples of the public EURES vacancy schema; no live network in tests."""

import copy
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from eures_beta.journeys.offer_ingestion import (
    ImportFailure,
    fetch_public,
    parse_page,
    read_url,
)

HANDLE = 'ZmljdGlvbmFsLWV1cmVzLWpvYi0xIDM'
URL = f'https://europa.eu/eures/portal/jv-se/jv-details/{HANDLE}'
API = (
    f'https://europa.eu/eures/api/jv-searchengine/public/jv/id/{HANDLE}?requestLang=en'
)


def vacancy():
    return {
        'id': HANDLE,
        'preferredLanguage': 'nl',
        'jvProfiles': {
            'nl': {
                'title': 'Fictieve ontwikkelaar',
                'description': '<p>Een fictieve vacature.</p>',
                'employer': {'name': 'Fictieve werkgever', 'cityName': 'Agency town'},
                'locations': [
                    {'cityName': 'Werkstad', 'postalCode': '1000', 'countryCode': 'be'}
                ],
                'positionScheduleCodes': ['fulltime'],
                'positionOfferingCode': 'directhire',
                'offeredRemunerationPackage': {
                    'benefitsSummaries': [
                        {
                            'otherBenefit': {
                                'description': '<p>Fictief loon: 4000 EUR.</p>'
                            }
                        }
                    ],
                },
            },
            'en': {
                'title': 'Fictional developer',
                'description': 'A fictional English vacancy.',
                'locations': [],
            },
        },
    }


class EuresImportTests(SimpleTestCase):
    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_handle_length_is_not_a_vacancy_validity_rule(self, fetch, target):
        for handle in ('QQ', 'ODM1MDEzOSA5', HANDLE, HANDLE + '=', 'A' * 220):
            with self.subTest(handle=handle):
                item = vacancy()
                item['id'] = handle
                endpoint = f'https://europa.eu/eures/api/jv-searchengine/public/jv/id/{handle}?requestLang=fr'
                fetch.reset_mock()
                fetch.return_value = (json.dumps(item), endpoint)
                url = f'https://europa.eu/eures/portal/jv-se/jv-details/{handle}?jvDisplayLanguage=nl&lang=fr'
                data, source = read_url(url)
                self.assertEqual(data['title'], 'Fictieve ontwikkelaar')
                self.assertEqual(source, url)
                fetch.assert_called_once_with(
                    endpoint, ('application/json',), allow_redirects=False
                )

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_unrecognized_eures_url_does_not_report_a_france_travail_listing(
        self, fetch, target
    ):
        for suffix in ('', '../private', HANDLE + '%2f..%2fprivate'):
            with self.subTest(suffix=suffix), self.assertRaises(ImportFailure) as error:
                read_url('https://europa.eu/eures/portal/jv-se/jv-details/' + suffix)
            self.assertEqual(error.exception.code, 'unreadable_url')
        fetch.assert_not_called()

    def test_initial_html_contains_only_the_loading_placeholder(self):
        with self.assertRaises(ImportFailure):
            parse_page('<html><body><app-root>Loading...</app-root></body></html>')

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_dynamic_offer_reads_public_json_without_browser_or_credentials(
        self, fetch, target
    ):
        fetch.return_value = (json.dumps(vacancy()), API)
        data, source = read_url(URL + '?jvDisplayLanguage=nl&lang=en')
        self.assertEqual(source, URL + '?jvDisplayLanguage=nl&lang=en')
        self.assertEqual(data['extraction'], 'eures_public')
        self.assertEqual(data['title'], 'Fictieve ontwikkelaar')
        self.assertEqual(data['companyName'], 'Fictieve werkgever')
        self.assertEqual(data['city'], '1000, Werkstad, BE')
        self.assertNotIn('Agency town', data['city'])
        self.assertIn('Een fictieve vacature.', data['description'])
        self.assertIn('Fictief loon: 4000 EUR.', data['description'])
        self.assertNotIn('<p>', data['description'])
        # Full time / direct hire do not establish a permanent contract.
        self.assertEqual(data['contractType'], '')
        fetch.assert_called_once_with(API, ('application/json',), allow_redirects=False)
        target.assert_called_once()

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_requested_profile_or_original_language_without_machine_translation(
        self, fetch, target
    ):
        fetch.return_value = (json.dumps(vacancy()), API)
        self.assertEqual(
            read_url(URL + '?jvDisplayLanguage=en')[0]['title'], 'Fictional developer'
        )
        self.assertEqual(
            read_url(URL + '?jvDisplayLanguage=de')[0]['title'], 'Fictieve ontwikkelaar'
        )

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_invalid_payloads_fail_instead_of_importing_the_site_shell(
        self, fetch, target
    ):
        invalid = ['not json', '[]', '{}']
        for change in (
            {'id': 'another-job'},
            {'jvProfiles': []},
            {'jvProfiles': {'nl': []}},
            {'jvProfiles': {'nl': {'title': 'No description'}}},
        ):
            item = copy.deepcopy(vacancy())
            item.update(change)
            invalid.append(json.dumps(item))
        for raw in invalid:
            with self.subTest(raw=raw):
                fetch.reset_mock()
                fetch.return_value = (raw, API)
                with self.assertRaises(ImportFailure):
                    read_url(URL)
                self.assertEqual(fetch.call_count, 1)

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_search_and_encoded_path_injections_are_not_vacancy_identifiers(
        self, fetch, target
    ):
        for url in (
            'https://europa.eu/eures/portal/jv-se/search',
            URL + '%2f..%2fprivate',
            URL + '/extra',
        ):
            with self.subTest(url=url), self.assertRaises(ImportFailure):
                read_url(url)
        fetch.assert_not_called()

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_url_security_validation_precedes_the_api_request(self, fetch, target):
        target.side_effect = ImportFailure('unsafe_url')
        for url in (
            URL.replace('https:', 'http:'),
            URL.replace('europa.eu', 'name:password@europa.eu'),
            URL.replace('europa.eu', 'europa.eu:444'),
        ):
            with self.subTest(url=url), self.assertRaises(ImportFailure):
                read_url(url)
        fetch.assert_not_called()

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_lookalike_host_never_uses_the_eures_api(self, fetch, target):
        lookalike = URL.replace('europa.eu', 'europa.eu.example.org')
        fetch.return_value = (
            '<title>Example</title><p>' + 'Fictional description. ' * 5 + '</p>',
            lookalike,
        )
        read_url(lookalike)
        fetch.assert_called_once_with(lookalike)

    @patch('eures_beta.journeys.offer_ingestion.PinnedHTTPS')
    @patch('eures_beta.journeys.offer_ingestion.public_target')
    def test_api_redirect_is_rejected_without_fetching_its_destination(
        self, target, connection
    ):
        from urllib.parse import urlsplit

        target.return_value = (urlsplit(API), 'europa.eu', '93.184.216.34')
        response = Mock(status=302)
        response.getheader.return_value = 'https://another.example.org/job'
        connection.return_value.getresponse.return_value = response
        with self.assertRaises(ImportFailure):
            fetch_public(API, ('application/json',), allow_redirects=False)
        self.assertEqual(target.call_count, 1)
        connection.return_value.close.assert_called_once()

    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_api_failure_does_not_fall_back_to_an_unrelated_html_page(
        self, fetch, target
    ):
        fetch.side_effect = ImportFailure('unreadable_url')
        with self.assertRaises(ImportFailure):
            read_url(URL)
        self.assertEqual(fetch.call_count, 1)


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class EuresSourceReviewTests(TestCase):
    @patch('eures_beta.journeys.offer_ingestion.public_target')
    @patch('eures_beta.journeys.offer_ingestion.fetch_public')
    def test_public_import_prepares_a_review_without_saving_an_offer(
        self, fetch, target
    ):
        from eures_beta.journeys.models import EmployerImport

        fetch.return_value = (json.dumps(vacancy()), API)
        refused = self.client.post('/api/imports/source/', {'url': URL}, secure=True)
        self.assertEqual(refused.status_code, 400)
        fetch.assert_not_called()
        response = self.client.post(
            '/api/imports/source/',
            {'url': URL + '?jvDisplayLanguage=nl', 'agreement': 'true'},
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['stage'], 'review')
        self.assertEqual(result['data']['title'], 'Fictieve ontwikkelaar')
        self.assertEqual(result['data']['extraction'], 'eures_public')
        self.assertEqual(
            self.client.session['pending_offer_source']['data'], result['data']
        )
        self.assertFalse(EmployerImport.objects.exists())
