from django.contrib.auth import get_user_model
import json
from unittest.mock import patch
from django.test import Client, TestCase
from eures_beta.employers.models import (
    Company,
    JobOffer,
    CompanyMembership,
)


class OwnershipTests(TestCase):
    def create(self, client=None):
        client = client or self.client
        # Existing unclaimed drafts are legacy fixtures, never created by the closed API.
        if not client.session.get('_auth_user_id'):
            from django.utils import timezone

            session = client.session
            session.save()
            offer = JobOffer.objects.create(
                created_by=get_user_model().objects.get_or_create(
                    email='first@fiction.invalid', defaults={'kind': 'employer'}
                )[0],
                session_key='',
                email='contact@fiction.invalid',
                preparation_agreed_at=timezone.now(),
                source_kind='manual',
                data={'description': 'Fictional role.'},
                contact={
                    'name': 'Fictional contact',
                    'email': 'contact@fiction.invalid',
                },
            )
            session['employer_claim_import'] = str(offer.pk)
            session.save()
            return {'id': str(offer.pk)}
        response = client.post(
            '/api/imports/',
            {
                'kind': 'manual',
                'text': 'Fictional role.',
                'email': 'contact@fiction.invalid',
                'agreement': 'true',
                'contact': json.dumps(
                    {'name': 'Fictional contact', 'email': 'contact@fiction.invalid'}
                ),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['login_url'], '/accounts/dashboard/')
        return response.json()

    def login(self, client, email):
        person, _ = get_user_model().objects.get_or_create(
            email=email, defaults={'kind': 'employer'}
        )
        client.force_login(person)
        return person

    def attach(self):
        draft = self.create()
        person = self.login(self.client, 'first@fiction.invalid')
        self.assertRedirects(
            self.client.post('/employer/attach/', {'name': 'Fictional company'}),
            '/employer/connected/',
        )
        return draft, person, Company.objects.get()

    def test_attachment_schedules_matching_after_commit(self):
        with (
            patch(
                'eures_beta.matching.services.calculate_for_saved_offer'
            ) as calculate,
            self.captureOnCommitCallbacks(execute=True),
        ):
            draft, _, _ = self.attach()
        offer = JobOffer.objects.get(pk=draft['id'])
        calculate.assert_called_once_with(offer.pk, offer.revision)

    def test_shared_offer_revocation_and_outsider(self):
        draft, person, company = self.attach()
        url = '/api/imports/' + draft['id'] + '/'
        other = Client()
        colleague = self.login(other, 'second@fiction.invalid')
        self.assertEqual(other.get(url).status_code, 404)
        membership = CompanyMembership.objects.create(person=colleague, company=company)
        self.assertEqual(other.get(url).json()['id'], draft['id'])
        payload = {
            'action': 'contact',
            'revision': 1,
            'contact': {'name': 'Other colleague', 'email': 'second@fiction.invalid'},
        }
        result = other.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            self.client.post(
                url, json.dumps(payload), content_type='application/json'
            ).status_code,
            409,
        )
        membership.active = False
        membership.save()
        self.assertEqual(other.get(url).status_code, 404)
        self.assertEqual(
            other.post(
                url, json.dumps(payload), content_type='application/json'
            ).status_code,
            404,
        )
        row = JobOffer.objects.get(pk=draft['id'])
        self.assertEqual(row.created_by, person)
        self.assertEqual(row.company, company)
        self.assertEqual(row.session_key, '')

    def test_reconnect_other_browser_logout_and_no_email_claim(self):
        draft, person, company = self.attach()
        url = '/api/imports/' + draft['id'] + '/'
        self.client.post('/accounts/logout/')
        self.assertEqual(self.client.get(url).status_code, 403)
        other = Client()
        self.assertEqual(self.login(other, person.email), person)
        self.assertEqual(other.get(url).status_code, 200)
        outsider = Client()
        self.login(outsider, 'contact@fiction.invalid')
        self.assertEqual(outsider.get(url).status_code, 404)
        self.assertEqual(
            outsider.post('/employer/attach/', {'company': company.pk}).status_code, 404
        )

    def test_cannot_select_an_unrelated_company_or_draft(self):
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        company = Company.objects.create(name='Unrelated')
        self.assertEqual(
            self.client.post('/employer/attach/', {'company': company.pk}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post('/employer/attach/', {'company': 'invalid'}).status_code,
            404,
        )
        row = JobOffer.objects.get(pk=draft['id'])
        self.assertIsNone(row.company)
        person = get_user_model().objects.get()
        CompanyMembership.objects.create(company=company, person=person)
        self.client.post(
            '/employer/attach/', {'company': company.pk, 'import': 'ignored'}
        )
        row.refresh_from_db()
        self.assertEqual(row.company, company)

    @patch('eures_beta.www.employer.imports.aglae')
    @patch('eures_beta.www.employer.imports.geocode')
    def test_no_external_submission_and_no_automatic_membership(self, geo, api):
        self.create()
        self.login(self.client, 'first@fiction.invalid')
        self.assertEqual(CompanyMembership.objects.count(), 0)
        geo.assert_not_called()
        api.assert_not_called()

    def test_translations_and_csrf(self):
        self.create()
        self.login(self.client, 'first@fiction.invalid')
        for lang, text in [
            ('fr', 'Rattacher votre offre'),
            ('en', 'Attach your offer'),
            ('de', 'Ihr Angebot einer Betriebsstätte'),
        ]:
            self.assertContains(
                self.client.get('/employer/connected/?lang=' + lang), text
            )
        self.assertEqual(self.client.get('/employer/attach/').status_code, 405)
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post('/employer/attach/', {'name': 'Fictional'})
            .status_code,
            403,
        )

    def test_unattached_draft_survives_logout_and_reconnection(self):
        draft = self.create()
        person = self.login(self.client, 'first@fiction.invalid')
        self.client.post('/accounts/logout/')
        other = Client()
        self.login(other, person.email)
        self.assertContains(other.get('/employer/connected/'), 'Rattacher votre offre')
        self.assertRedirects(
            other.post('/employer/attach/', {'name': 'Fictional workspace'}),
            '/employer/connected/',
        )
        self.assertEqual(
            other.get('/api/imports/' + draft['id'] + '/').status_code, 200
        )

    def test_first_establishment_requires_only_a_name(self):
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        screen = self.client.get('/employer/connected/')
        self.assertContains(screen, 'Nom de l’établissement')
        self.assertNotContains(screen, 'name="country"')
        self.assertNotContains(screen, 'name="registration_id"')
        self.assertContains(
            self.client.post('/employer/attach/', {'name': '  '}), 'Renseignez le nom'
        )
        self.assertIsNone(JobOffer.objects.get(pk=draft['id']).company)
        self.assertRedirects(
            self.client.post('/employer/attach/', {'name': 'Fictional establishment'}),
            '/employer/connected/',
        )
        self.assertEqual(Company.objects.get().name, 'Fictional establishment')

    def test_existing_member_cannot_create_another_establishment(self):
        _, _, company = self.attach()
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        screen = self.client.get('/employer/connected/')
        self.assertContains(screen, 'Enregistrer l’offre pour cet établissement')
        self.assertNotContains(screen, 'name="name"')
        self.assertNotContains(screen, 'Enregistrer un autre établissement')
        self.assertEqual(
            self.client.post('/employer/attach/', {'name': 'Another'}).status_code, 404
        )
        self.assertEqual(Company.objects.count(), 1)
        self.assertIsNone(JobOffer.objects.get(pk=draft['id']).company)
        self.client.post('/employer/attach/', {'company': company.pk})
        self.assertEqual(JobOffer.objects.get(pk=draft['id']).company, company)

    def test_multiple_memberships_require_explicit_choice(self):
        _, person, first = self.attach()
        second = Company.objects.create(name='Second establishment')
        CompanyMembership.objects.create(person=person, company=second)
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        screen = self.client.get('/employer/connected/')
        self.assertContains(screen, 'id="establishment-choice"')
        self.assertEqual(self.client.post('/employer/attach/', {}).status_code, 404)
        self.assertIsNone(JobOffer.objects.get(pk=draft['id']).company)
        self.client.post('/employer/attach/', {'company': second.pk})
        self.assertEqual(JobOffer.objects.get(pk=draft['id']).company, second)

    def test_name_match_does_not_grant_access(self):
        draft, _, existing = self.attach()
        other = Client()
        outsider = self.login(other, 'outsider@fiction.invalid')
        self.create(other)
        other.post('/employer/attach/', {'name': existing.name})
        self.assertEqual(Company.objects.count(), 2)
        self.assertFalse(
            CompanyMembership.objects.filter(company=existing, person=outsider).exists()
        )
        self.assertEqual(
            other.get('/api/imports/' + draft['id'] + '/').status_code, 404
        )
