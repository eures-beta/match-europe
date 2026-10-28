import json
from unittest.mock import patch
from django.test import TestCase
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from eures_beta.journeys.models import (
    EmployerCompany,
    EmployerImport,
    EmployerMembership,
)
from eures_beta.journeys.tests.test_employer_ownership import OwnershipTests


@patch.dict(
    'os.environ',
    {
        'ME_EMPLOYER_EMAIL_LOCAL': '1',
        'ME_EMPLOYER_DEV_ACCESS': '1',
        'ME_LOCAL_REVIEW_ONLY': '1',
    },
)
class ConnectedEmployerTests(TestCase):
    login = OwnershipTests.login

    def submit(self, client=None):
        return (client or self.client).post(
            '/api/imports/',
            {
                'kind': 'manual',
                'text': 'Fictional role',
                'agreement': 'true',
                'connectedSubmission': 'true',
                'contact': json.dumps(
                    {'name': 'Adviser contact', 'email': 'adviser@fiction.invalid'}
                ),
            },
        )

    def test_access_without_offer_and_languages(self):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        company = EmployerCompany.objects.create(name='Allowed establishment')
        EmployerMembership.objects.create(person=person, company=company)
        EmployerCompany.objects.create(name='Hidden establishment')
        for lang, label in [
            ('fr', 'Ajouter une offre'),
            ('en', 'Add an offer'),
            ('de', 'Angebot hinzufügen'),
        ]:
            page = self.client.get('/employer/connected/?lang=' + lang)
            self.assertContains(page, label)
            self.assertContains(page, company.name)
            self.assertNotContains(page, 'Hidden establishment')
        self.assertEqual(EmployerImport.objects.count(), 0)
        self.assertRedirects(
            self.client.get('/employer/access/'), '/employer/connected/'
        )

    @patch('eures_beta.journeys.employer_api.aglae')
    @patch('eures_beta.journeys.employer_api.geocode')
    def test_valid_session_and_distinct_contact(self, geo, api):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        company = EmployerCompany.objects.create(name='Allowed establishment')
        EmployerMembership.objects.create(person=person, company=company)
        key = self.client.session.session_key
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['login_url'], '/employer/connected/')
        self.assertEqual(key, self.client.session.session_key)
        draft = EmployerImport.objects.get()
        self.assertEqual(draft.created_by, person)
        self.assertEqual(draft.contact['email'], 'adviser@fiction.invalid')
        self.client.post('/employer/attach/', {'company': company.pk})
        draft.refresh_from_db()
        self.assertEqual(draft.company, company)
        self.assertEqual(draft.session_key, '')
        geo.assert_not_called()
        api.assert_not_called()

    def test_multiple_establishments_and_forbidden_choice(self):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        companies = [
            EmployerCompany.objects.create(name=name)
            for name in ['First', 'Second', 'Forbidden']
        ]
        for company in companies[:2]:
            EmployerMembership.objects.create(person=person, company=company)
        self.submit()
        self.assertContains(
            self.client.get('/employer/connected/'), 'id="establishment-choice"'
        )
        for payload in [{}, {'company': companies[2].pk}]:
            self.assertEqual(
                self.client.post('/employer/attach/', payload).status_code, 404
            )
            self.assertIsNone(EmployerImport.objects.get().company)
        self.client.post('/employer/attach/', {'company': companies[1].pk})
        self.assertEqual(EmployerImport.objects.get().company, companies[1])

    def test_expired_session_preserves_draft_without_rights(self):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['login_url'], '/employer/access/')
        draft = EmployerImport.objects.get()
        self.assertIsNone(draft.created_by)
        self.assertIsNone(draft.company)
        self.login(self.client, person.email)
        draft.refresh_from_db()
        self.assertEqual(draft.created_by, person)

    def test_no_membership_and_revocation(self):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        self.assertContains(
            self.client.get('/employer/connected/'), 'Vous n’êtes encore'
        )
        company = EmployerCompany.objects.create(name='Revoked')
        EmployerMembership.objects.create(person=person, company=company, active=False)
        self.submit()
        self.assertEqual(
            self.client.post('/employer/attach/', {'company': company.pk}).status_code,
            404,
        )

    def test_v2_connection_button_and_server_session_state(self):
        for lang, label in [
            ('fr', 'Me connecter'),
            ('en', 'Sign in'),
            ('de', 'Anmelden'),
        ]:
            path = '/employer/pages/import-v2-' + lang + '.html'
            self.assertContains(self.client.get(path), label)
        self.login(self.client, 'rh1@entreprise.invalid')
        self.assertContains(self.client.get(path), 'data-employer-connected="true"')
        self.assertContains(self.client.get(path), 'Mein Arbeitgeberbereich')
        self.assertContains(
            self.client.get('/employer/connected/?lang=fr'), 'Mon espace employeur'
        )
        self.client.post('/employer/logout/')
        self.assertContains(self.client.get(path), 'data-employer-connected="false"')

    def test_expired_document_session_explains_reread(self):
        self.login(self.client, 'rh1@entreprise.invalid')
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        response = self.client.post(
            '/api/imports/', {'kind': 'pdf', 'connectedSubmission': 'true'}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'session_expired')
        self.assertFalse(EmployerImport.objects.exists())
