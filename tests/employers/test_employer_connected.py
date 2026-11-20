import json
from unittest.mock import patch
from django.test import TestCase
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from eures_beta.employers.models import (
    JobOffer,
)
from tests.employers.test_employer_ownership import OwnershipTests


class ConnectedEmployerTests(TestCase):
    login = OwnershipTests.login

    def submit(self, client=None):
        return (client or self.client).post(
            '/api/job-offers/',
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
        for lang, label in [
            ('fr', 'Décrire mon besoin de recrutement'),
            ('en', 'Describe my recruitment needs'),
            ('de', 'Meinen Personalbedarf beschreiben'),
        ]:
            page = self.client.get('/accounts/dashboard/?lang=' + lang)
            self.assertContains(page, label)
        self.assertEqual(JobOffer.objects.count(), 0)
        self.assertEqual(self.client.get('/employer/access/').status_code, 404)

    @patch('eures_beta.www.employer.imports.aglae')
    @patch('eures_beta.www.employer.imports.geocode')
    def test_valid_session_and_distinct_contact(self, geo, api):
        person = self.login(self.client, 'rh1@entreprise.invalid')
        key = self.client.session.session_key
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['login_url'], '/accounts/dashboard/')
        self.assertEqual(key, self.client.session.session_key)
        draft = JobOffer.objects.get()
        self.assertEqual(draft.employer, person)
        self.assertNotIn('email', draft.contact)
        self.assertEqual(draft.employer.email, person.email)
        self.assertEqual(draft.session_key, '')
        geo.assert_not_called()
        api.assert_not_called()

    def test_expired_session_cannot_create_a_draft(self):
        self.login(self.client, 'rh1@entreprise.invalid')
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        response = self.submit()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(JobOffer.objects.exists())

    def test_import_connection_button_and_server_session_state(self):
        for lang, label in [
            ('fr', 'Se connecter'),
            ('en', 'Sign in'),
            ('de', 'Anmelden'),
        ]:
            path = '/employer/import/?lang=' + lang
            self.assertContains(self.client.get(path), label)
        self.login(self.client, 'rh1@entreprise.invalid')
        self.assertContains(self.client.get(path), 'data-employer-connected="true"')
        self.assertContains(self.client.get(path), 'Mein Konto')
        self.assertContains(
            self.client.get('/accounts/dashboard/?lang=fr'), 'Vos offres'
        )
        self.client.post('/accounts/logout/')
        self.assertTemplateUsed(self.client.get(path), 'employer/import_access.html')

    def test_expired_document_session_explains_reread(self):
        self.login(self.client, 'rh1@entreprise.invalid')
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        response = self.client.post(
            '/api/job-offers/', {'kind': 'pdf', 'connectedSubmission': 'true'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'employer_account_required')
        self.assertFalse(JobOffer.objects.exists())
