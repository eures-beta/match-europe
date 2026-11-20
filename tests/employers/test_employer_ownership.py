"""Offer ownership is personal, never inferred from contact or browser data."""

import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from eures_beta.employers.models import JobOffer


class OwnershipTests(TestCase):
    def login(self, client, email):
        person, _ = get_user_model().objects.get_or_create(
            email=email, defaults={'kind': 'employer'}
        )
        client.force_login(person)
        return person

    def create(self, client=None):
        response = (client or self.client).post(
            '/api/job-offers/',
            {
                'kind': 'manual',
                'text': 'Fictional role.',
                'agreement': 'true',
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'contact@fiction.invalid'}
                ),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['login_url'], '/accounts/dashboard/')
        return response.json()

    def test_offer_is_owned_at_creation_and_matching_is_scheduled(self):
        person = self.login(self.client, 'first@fiction.invalid')
        with (
            patch(
                'eures_beta.matching.services.calculate_for_saved_offer'
            ) as calculate,
            self.captureOnCommitCallbacks(execute=True),
        ):
            draft = self.create()
        offer = JobOffer.objects.get(pk=draft['id'])
        self.assertEqual(offer.employer, person)
        self.assertEqual(offer.session_key, '')
        calculate.assert_called_once_with(offer.pk, offer.revision)
        dashboard = self.client.get(reverse('dashboard'))
        self.assertEqual(list(dashboard.context['offers']), [offer])
        self.assertContains(dashboard, reverse('employer_offer', args=[offer.pk]))

    def test_contact_and_old_company_parameters_never_grant_access(self):
        self.login(self.client, 'first@fiction.invalid')
        draft = self.create()
        other = Client()
        self.login(other, 'contact@fiction.invalid')
        url = reverse('job_offer_data', args=[draft['id']])
        for method in ('get', 'post'):
            self.assertEqual(
                getattr(other, method)(
                    url, {'company': '1', 'employer': '1'}
                ).status_code,
                404,
            )
        self.assertNotContains(other.get(reverse('dashboard')), 'Fictional role.')

    def test_reconnect_another_browser_and_logout(self):
        person = self.login(self.client, 'first@fiction.invalid')
        draft = self.create()
        url = reverse('job_offer_data', args=[draft['id']])
        self.client.post('/accounts/logout/')
        self.assertEqual(self.client.get(url).status_code, 403)
        other = Client()
        self.login(other, person.email)
        self.assertEqual(other.get(url).status_code, 200)

    def test_unowned_browser_draft_cannot_be_claimed(self):
        self.login(self.client, 'first@fiction.invalid')
        offer = JobOffer.objects.create(
            session_key=self.client.session.session_key,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': 'Unclaimed secret'},
        )
        self.assertEqual(
            self.client.get(reverse('job_offer_data', args=[offer.pk])).status_code, 404
        )
        self.assertNotContains(
            self.client.get(reverse('dashboard')), 'Unclaimed secret'
        )
        self.assertEqual(
            self.client.post('/employer/attach/', {'name': 'Ignored'}).status_code, 410
        )
        self.assertEqual(
            self.client.post(f'/employer/drafts/{offer.pk}/attach/').status_code, 410
        )
        offer.refresh_from_db()
        self.assertIsNone(offer.employer)

    @patch('eures_beta.www.employer.imports.aglae')
    @patch('eures_beta.www.employer.imports.geocode')
    def test_no_external_submission(self, geo, api):
        self.login(self.client, 'first@fiction.invalid')
        self.create()
        geo.assert_not_called()
        api.assert_not_called()
