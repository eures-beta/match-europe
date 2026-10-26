import json
from unittest.mock import patch
from django.test import Client, TestCase
from .models import (
    EmployerCompany,
    EmployerIdentity,
    EmployerImport,
    EmployerMembership,
)


@patch.dict(
    'os.environ',
    {
        'ME_EMPLOYER_EMAIL_LOCAL': '1',
        'ME_EMPLOYER_DEV_ACCESS': '1',
        'ME_LOCAL_REVIEW_ONLY': '1',
    },
)
class OwnershipTests(TestCase):
    def create(self, client=None):
        client = client or self.client
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
        self.assertEqual(
            response.json()['login_url'],
            (
                '/employer/connected/'
                if client.session.get('employer_identity_id')
                else '/employer/access/'
            ),
        )
        return response.json()

    def login(self, client, email):
        session = client.session
        if session.get('employer_verified_email') == email:
            return EmployerIdentity.objects.get(email=email)
        session['employer_email_sent_at'] = 0
        session.save()
        client.post('/employer/access/', {'email': email})
        link = client.session['employer_test_message']['link']
        client.post(link)
        return EmployerIdentity.objects.get(email=email)

    def attach(self):
        draft = self.create()
        self.assertContains(
            self.client.get('/employer/access/'), 'value="contact@fiction.invalid"'
        )
        person = self.login(self.client, 'first@fiction.invalid')
        self.assertRedirects(
            self.client.post('/employer/attach/', {'name': 'Fictional company'}),
            '/employer/connected/',
        )
        return draft, person, EmployerCompany.objects.get()

    def test_shared_offer_revocation_and_outsider(self):
        draft, person, company = self.attach()
        url = '/api/imports/' + draft['id'] + '/'
        other = Client()
        colleague = self.login(other, 'second@fiction.invalid')
        self.assertEqual(other.get(url).status_code, 404)
        membership = EmployerMembership.objects.create(
            person=colleague, company=company
        )
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
        row = EmployerImport.objects.get(pk=draft['id'])
        self.assertEqual(row.created_by, person)
        self.assertEqual(row.company, company)
        self.assertEqual(row.session_key, '')

    def test_reconnect_other_browser_logout_and_no_email_claim(self):
        draft, person, company = self.attach()
        url = '/api/imports/' + draft['id'] + '/'
        self.client.post('/employer/logout/')
        self.assertEqual(self.client.get(url).status_code, 404)
        other = Client()
        self.assertEqual(self.login(other, person.email), person)
        self.assertEqual(other.get(url).status_code, 200)
        outsider = Client()
        self.login(outsider, 'contact@fiction.invalid')
        self.assertEqual(outsider.get(url).status_code, 404)
        self.assertEqual(
            outsider.post('/employer/attach/', {'company': company.pk}).status_code, 404
        )

    def test_draft_survives_link_opened_in_other_browser(self):
        draft = self.create()
        self.client.post('/employer/access/', {'email': 'first@fiction.invalid'})
        link = self.client.session['employer_test_message']['link']
        other = Client()
        other.post(link)
        self.assertContains(other.get('/employer/connected/'), 'Rattacher votre offre')
        other.post('/employer/attach/', {'name': 'Fictional company'})
        url = '/api/imports/' + draft['id'] + '/'
        self.assertEqual(other.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            other.post('/employer/attach/', {'name': 'Duplicate'}).status_code, 404
        )
        self.assertEqual(EmployerCompany.objects.count(), 1)

    def test_cannot_select_an_unrelated_company_or_draft(self):
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        company = EmployerCompany.objects.create(name='Unrelated')
        self.assertEqual(
            self.client.post('/employer/attach/', {'company': company.pk}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post('/employer/attach/', {'company': 'invalid'}).status_code,
            404,
        )
        row = EmployerImport.objects.get(pk=draft['id'])
        self.assertIsNone(row.company)
        person = EmployerIdentity.objects.get()
        EmployerMembership.objects.create(company=company, person=person)
        self.client.post(
            '/employer/attach/', {'company': company.pk, 'import': 'ignored'}
        )
        row.refresh_from_db()
        self.assertEqual(row.company, company)

    @patch('eures_beta.journeys.employer_api.aglae')
    @patch('eures_beta.journeys.employer_api.geocode')
    def test_no_external_submission_and_no_automatic_membership(self, geo, api):
        self.create()
        self.login(self.client, 'first@fiction.invalid')
        self.assertEqual(EmployerMembership.objects.count(), 0)
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
        self.client.post('/employer/logout/')
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
        self.assertIsNone(EmployerImport.objects.get(pk=draft['id']).company)
        self.assertRedirects(
            self.client.post('/employer/attach/', {'name': 'Fictional establishment'}),
            '/employer/connected/',
        )
        self.assertEqual(EmployerCompany.objects.get().name, 'Fictional establishment')

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
        self.assertEqual(EmployerCompany.objects.count(), 1)
        self.assertIsNone(EmployerImport.objects.get(pk=draft['id']).company)
        self.client.post('/employer/attach/', {'company': company.pk})
        self.assertEqual(EmployerImport.objects.get(pk=draft['id']).company, company)

    def test_multiple_memberships_require_explicit_choice(self):
        _, person, first = self.attach()
        second = EmployerCompany.objects.create(name='Second establishment')
        EmployerMembership.objects.create(person=person, company=second)
        draft = self.create()
        self.login(self.client, 'first@fiction.invalid')
        screen = self.client.get('/employer/connected/')
        self.assertContains(screen, 'id="establishment-choice"')
        self.assertEqual(self.client.post('/employer/attach/', {}).status_code, 404)
        self.assertIsNone(EmployerImport.objects.get(pk=draft['id']).company)
        self.client.post('/employer/attach/', {'company': second.pk})
        self.assertEqual(EmployerImport.objects.get(pk=draft['id']).company, second)

    def test_name_match_does_not_grant_access(self):
        draft, _, existing = self.attach()
        other = Client()
        self.create(other)
        outsider = self.login(other, 'outsider@fiction.invalid')
        other.post('/employer/attach/', {'name': existing.name})
        self.assertEqual(EmployerCompany.objects.count(), 2)
        self.assertFalse(
            EmployerMembership.objects.filter(
                company=existing, person=outsider
            ).exists()
        )
        self.assertEqual(
            other.get('/api/imports/' + draft['id'] + '/').status_code, 404
        )
