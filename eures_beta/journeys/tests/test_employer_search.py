import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from ..models import (
    EmployerImport,
    EmployerIdentity,
    EmployerMembership,
    EmployerSearchOperation,
    EmployerSearchEvent,
)
from . import test_employer_workspace as workspace_tests

MODES = {
    'ME_EMPLOYER_DEV_ACCESS': '1',
    'ME_EMPLOYER_EMAIL_LOCAL': '1',
    'ME_LOCAL_REVIEW_ONLY': '1',
    'ME_EMPLOYER_SEARCH_SIMULATION': '1',
}


class SearchSetup:
    setUp = workspace_tests.WorkspaceTests.setUp
    login = workspace_tests.WorkspaceTests.login
    make_offer = workspace_tests.WorkspaceTests.make_offer
    url = workspace_tests.WorkspaceTests.url
    payload = workspace_tests.WorkspaceTests.payload

    def launch(self, scenario='success', revision=1, client=None):
        return (client or self.client).post(
            self.url('employer_search_launch'),
            {'revision': revision, 'confirmed': 'on', 'scenario': scenario},
        )


@patch.dict('os.environ', MODES)
class SearchTests(SearchSetup, TestCase):
    def test_confirmation_and_start_replay_no_external_calls(self):
        with (
            patch('eures_beta.journeys.employer_api.aglae') as external,
            patch('eures_beta.journeys.employer_api.geocode') as geo,
        ):
            self.assertContains(
                self.client.get(self.url('employer_search_launch')), 'qualification'
            )
            self.assertFalse(EmployerSearchOperation.objects.exists())
            self.launch()
            self.launch()
            self.offer.refresh_from_db()
            self.assertIsNotNone(self.offer.search_started_at)
            self.assertEqual(self.offer.revision, 2)
            self.assertEqual(EmployerSearchOperation.objects.count(), 1)
            self.assertEqual(EmployerSearchEvent.objects.count(), 2)
            self.assertEqual(
                self.client.post(
                    self.url('employer_offer_edit'), self.payload()
                ).status_code,
                409,
            )
            self.assertEqual(
                self.client.post(
                    self.url('employer_offer_duplicate'), {'revision': 2}
                ).status_code,
                302,
            )
            copy = EmployerImport.objects.get(duplicated_from=self.offer)
            self.assertIsNone(copy.search_started_at)
            self.assertFalse(copy.search_operations.exists())
            external.assert_not_called()
            geo.assert_not_called()

    def test_failure_requires_fresh_confirmation_not_replayed_post(self):
        self.launch('failure')
        self.launch('success')
        self.offer.refresh_from_db()
        self.assertIsNone(self.offer.search_started_at)
        self.assertFalse(self.offer.search_write_blocked)
        self.assertEqual(EmployerSearchOperation.objects.count(), 1)
        self.launch('success', revision=self.offer.revision)
        self.offer.refresh_from_db()
        self.assertIsNotNone(self.offer.search_started_at)
        self.assertEqual(EmployerSearchOperation.objects.count(), 2)

    def test_uncertain_blocks_all_writes_and_checks_without_new_launch(self):
        for scenario, started in [
            ('timeout_accepted', True),
            ('timeout_rejected', False),
        ]:
            with self.subTest(scenario=scenario):
                self.offer = self.make_offer(self.company, 'Uncertain fictional offer')
                self.launch(scenario)
                self.launch(scenario)
                self.offer.refresh_from_db()
                self.assertIsNone(self.offer.search_started_at)
                self.assertTrue(self.offer.search_write_blocked)
                self.assertContains(self.client.get(self.url()), 'Démarrage à vérifier')
                self.assertEqual(
                    self.client.post(
                        self.url('employer_offer_edit'), self.payload()
                    ).status_code,
                    409,
                )
                for action in ('save', 'contact', 'prepare', 'validate', 'locate'):
                    response = self.client.post(
                        '/api/imports/' + str(self.offer.pk) + '/',
                        json.dumps(
                            {
                                'action': action,
                                'revision': 1,
                                'data': self.offer.data,
                                'contact': self.offer.contact,
                            }
                        ),
                        content_type='application/json',
                    )
                    self.assertEqual(response.status_code, 409)
                self.client.post(self.url('employer_search_check'))
                self.client.post(self.url('employer_search_check'))
                self.offer.refresh_from_db()
                self.assertEqual(bool(self.offer.search_started_at), started)
                self.assertEqual(self.offer.search_operations.count(), 1)
                self.assertEqual(self.offer.search_operations.get().events.count(), 3)

    def test_revision_conflict_both_directions(self):
        self.client.post(self.url('employer_offer_edit'), self.payload())
        self.assertEqual(self.launch().status_code, 409)
        self.assertFalse(EmployerSearchOperation.objects.exists())
        self.launch(revision=2)
        self.assertEqual(
            self.client.post(
                self.url('employer_offer_edit'), self.payload()
            ).status_code,
            409,
        )

    def test_permissions_confirmation_csrf_and_simulation_gate(self):
        endpoint = self.url('employer_search_launch')
        self.assertEqual(
            self.client.post(
                endpoint, {'revision': 1, 'scenario': 'success'}
            ).status_code,
            200,
        )
        self.assertFalse(EmployerSearchOperation.objects.exists())
        self.assertEqual(
            self.client.post(
                endpoint, {'revision': 1, 'confirmed': 'on', 'scenario': 'arbitrary'}
            ).status_code,
            200,
        )
        secured = Client(enforce_csrf_checks=True)
        self.login(secured, self.person)
        self.assertEqual(self.launch(client=secured).status_code, 403)
        self.assertEqual(
            secured.post(self.url('employer_search_check')).status_code, 403
        )
        self.assertEqual(
            self.client.get(self.url('employer_search_check')).status_code, 405
        )
        for action in ('employer_search_launch', 'employer_search_check'):
            self.assertEqual(
                self.client.post(
                    self.url(action, self.foreign),
                    {'revision': 1, 'confirmed': 'on', 'scenario': 'success'},
                ).status_code,
                404,
            )
        EmployerMembership.objects.filter(person=self.person).update(active=False)
        self.assertEqual(self.launch().status_code, 404)
        self.assertEqual(
            self.client.post(self.url('employer_search_check')).status_code, 404
        )
        self.client.session.flush()
        anon = Client()
        self.assertEqual(self.launch(client=anon).status_code, 302)
        EmployerMembership.objects.filter(person=self.person).update(active=True)
        self.client = Client()
        self.login(self.client, self.person)
        for changes in (
            {'ME_LOCAL_REVIEW_ONLY': '0'},
            {'ME_EMPLOYER_SEARCH_SIMULATION': '0'},
        ):
            with patch.dict('os.environ', changes):
                self.assertEqual(self.launch().status_code, 404)
                self.assertNotContains(
                    self.client.get(self.url()), 'Lancer ma recherche'
                )
        self.assertFalse(EmployerSearchOperation.objects.exists())

    def test_languages(self):
        for lang, text in [
            ('fr', 'Lancer ma recherche de candidats'),
            ('en', 'Start my candidate search'),
            ('de', 'Meine Kandidatensuche starten'),
        ]:
            self.assertContains(
                self.client.get(self.url('employer_search_launch') + '?lang=' + lang),
                text,
            )


@patch.dict('os.environ', MODES)
class SearchConcurrencyTests(SearchSetup, TransactionTestCase):
    def test_two_colleagues_start_same_revision_once(self):
        colleague = EmployerIdentity.objects.create(email='rh2@fiction.invalid')
        EmployerMembership.objects.create(person=colleague, company=self.company)
        clients = [Client(), Client()]
        self.login(clients[0], self.person)
        self.login(clients[1], colleague)
        barrier = Barrier(2)

        def start(client):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.launch(client=client).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(start, clients)), [302, 302])
        self.assertEqual(EmployerSearchOperation.objects.count(), 1)
        self.assertEqual(EmployerSearchEvent.objects.count(), 2)

    def test_edit_and_start_race_never_start_an_unconfirmed_revision(self):
        clients = [Client(), Client()]
        for client in clients:
            self.login(client, self.person)
        values = self.payload()
        values['title'] = 'Concurrent fictional change'
        barrier = Barrier(2)

        def act(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                if index == 0:
                    return self.launch(client=clients[0]).status_code
                return (
                    clients[1].post(self.url('employer_offer_edit'), values).status_code
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, [0, 1]))
        self.offer.refresh_from_db()
        if self.offer.search_started_at:
            self.assertEqual(results, [302, 409])
            self.assertEqual(self.offer.data['title'], 'Fictional technician')
        else:
            self.assertEqual(results, [409, 302])
            self.assertEqual(self.offer.data['title'], 'Concurrent fictional change')
            self.assertFalse(EmployerSearchOperation.objects.exists())
