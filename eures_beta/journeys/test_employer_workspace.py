import json
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone
from django.urls import reverse
from .models import (
    EmployerImport,
    EmployerIdentity,
    EmployerMembership,
    EmployerCompany,
)
from .offer_ingestion import empty_data


@patch.dict(
    'os.environ',
    {
        'ME_EMPLOYER_DEV_ACCESS': '1',
        'ME_EMPLOYER_EMAIL_LOCAL': '1',
        'ME_LOCAL_REVIEW_ONLY': '1',
    },
)
class WorkspaceTests(TestCase):
    def setUp(self):
        self.person = EmployerIdentity.objects.create(email='rh1@fiction.invalid')
        self.company = EmployerCompany.objects.create(name='First establishment')
        EmployerMembership.objects.create(company=self.company, person=self.person)
        self.other = EmployerCompany.objects.create(name='Other establishment')
        self.login(self.client, self.person)
        self.offer = self.make_offer(self.company, title='Fictional technician')
        self.foreign = self.make_offer(self.other, title='Hidden foreign offer')

    def login(self, client, person):
        session = client.session
        session['employer_identity_id'] = person.pk
        session['employer_verified_email'] = person.email
        session.save()

    def make_offer(self, company, title):
        data = empty_data()
        data.update(
            title=title,
            companyName='Company in text',
            city='Metz',
            description='Fictional description',
        )
        return EmployerImport.objects.create(
            company=company,
            created_by=self.person,
            session_key='',
            email=self.person.email,
            contact={'name': 'Contact person', 'email': 'contact@fiction.invalid'},
            data=data,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
        )

    def url(self, action='employer_offer', offer=None):
        return reverse(action, args=[(offer or self.offer).pk])

    def payload(self, offer=None):
        from .employer_workspace import OfferEditForm

        offer = offer or self.offer
        form = OfferEditForm(offer=offer)
        payload = {field.name: field.value() or '' for field in form}
        for name in ('workConditions', 'permits', 'arrivalAids'):
            payload[name] = payload[name] or []
        payload.update(
            {
                'contact-name': 'Separate contact',
                'contact-email': 'other-contact@fiction.invalid',
            }
        )
        return payload

    def test_list_filter_and_privacy(self):
        response = self.client.get('/employer/offers/')
        self.assertContains(response, self.offer.data['title'])
        self.assertNotContains(response, self.foreign.data['title'])
        self.assertEqual(
            self.client.get(
                '/employer/offers/?company=' + str(self.other.pk)
            ).status_code,
            404,
        )
        EmployerMembership.objects.create(company=self.other, person=self.person)
        self.assertContains(
            self.client.get('/employer/offers/'), self.foreign.data['title']
        )
        page = self.client.get('/employer/offers/?company=' + str(self.other.pk))
        self.assertContains(page, self.foreign.data['title'])
        self.assertNotContains(page, self.offer.data['title'])

    def test_no_membership_empty_and_no_name_email_access(self):
        outsider = EmployerIdentity.objects.create(email='contact@fiction.invalid')
        client = Client()
        self.login(client, outsider)
        self.assertContains(client.get('/employer/offers/'), 'Aucune offre')
        for name in ('employer_offer', 'employer_offer_edit'):
            self.assertEqual(client.get(self.url(name)).status_code, 404)
        self.assertEqual(
            client.post(
                self.url('employer_offer_duplicate'), {'revision': 1}
            ).status_code,
            404,
        )

    def test_detail_edit_preserve_metadata_and_establishment(self):
        self.offer.data.update(
            extraction='pdf_text',
            questions=[{'question': 'Fictional question?', 'mandatory': False}],
            custom='preserved',
        )
        self.offer.data['clarifications']['salary'] = '3000 EUR'
        self.offer.save()
        self.assertContains(self.client.get(self.url()), 'Fictional description')
        values = self.payload()
        values['title'] = 'Updated fictional role'
        values['companyName'] = 'Other establishment'
        values['company'] = self.other.pk
        values['search_started_at'] = 'ignored'
        response = self.client.post(self.url('employer_offer_edit'), values)
        self.assertEqual(response.status_code, 302)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.data['title'], 'Updated fictional role')
        self.assertEqual(self.offer.data['custom'], 'preserved')
        self.assertEqual(self.offer.company, self.company)
        self.assertEqual(self.offer.created_by, self.person)
        self.assertEqual(self.offer.contact['email'], 'other-contact@fiction.invalid')
        self.assertIsNone(self.offer.search_started_at)
        self.assertEqual(self.offer.revision, 2)
        self.assertContains(self.client.get(response.url), 'Modifications enregistrées')

    def test_invalid_contact_and_conflict_do_not_erase(self):
        values = self.payload()
        values['contact-email'] = 'invalid'
        self.assertContains(
            self.client.post(self.url('employer_offer_edit'), values),
            'pas été enregistrées',
        )
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.revision, 1)
        values = self.payload()
        self.offer.revision = 2
        self.offer.save()
        self.assertContains(
            self.client.post(self.url('employer_offer_edit'), values),
            'Un collègue a modifié',
        )
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.revision, 2)
        self.assertEqual(self.offer.data['title'], 'Fictional technician')

    def test_revoked_access_and_expired_session(self):
        values = self.payload()
        EmployerMembership.objects.filter(person=self.person).update(active=False)
        self.assertEqual(
            self.client.post(self.url('employer_offer_edit'), values).status_code, 404
        )
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        Session.objects.filter(session_key=self.client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        self.assertRedirects(self.client.get('/employer/offers/'), '/employer/access/')
        self.assertRedirects(
            self.client.post(self.url('employer_offer_edit'), values),
            '/employer/access/',
        )

    def test_lock_covers_new_editor_and_old_api(self):
        values = self.payload()
        self.offer.search_started_at = timezone.now()
        self.offer.save()
        self.assertNotContains(
            self.client.get(self.url()),
            'href="' + self.url('employer_offer_edit') + '"',
        )
        self.assertEqual(
            self.client.post(self.url('employer_offer_edit'), values).status_code, 409
        )
        for action in ('save', 'contact', 'prepare', 'validate', 'locate'):
            payload = {
                'action': action,
                'revision': 1,
                'data': self.offer.data,
                'contact': self.offer.contact,
            }
            response = self.client.post(
                '/api/imports/' + str(self.offer.pk) + '/',
                json.dumps(payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()['error'], 'search_started')
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.revision, 1)

    def test_sent_or_validated_is_not_search_started(self):
        self.offer.initial_sent_at = self.offer.synced_at = self.offer.validated_at = (
            timezone.now()
        )
        self.offer.save()
        self.assertEqual(
            self.client.post(
                self.url('employer_offer_edit'), self.payload()
            ).status_code,
            302,
        )
        self.offer.refresh_from_db()
        self.assertIsNone(self.offer.search_started_at)

    @patch('eures_beta.journeys.employer_api.aglae')
    @patch('eures_beta.journeys.employer_api.geocode')
    def test_duplicate_resets_state_and_shares_only_authorised(self, geo, external):
        self.offer.search_started_at = self.offer.initial_sent_at = (
            self.offer.synced_at
        ) = self.offer.validated_at = timezone.now()
        self.offer.sandbox_response = {'external': 'must-not-copy'}
        self.offer.data['geo'] = {'query': 'Metz'}
        self.offer.save()
        original = deepcopy(self.offer.data)
        response = self.client.post(
            self.url('employer_offer_duplicate'), {'revision': 1}
        )
        self.assertEqual(response.status_code, 302)
        copy = EmployerImport.objects.get(duplicated_from=self.offer)
        self.assertNotEqual(copy.pk, self.offer.pk)
        self.assertEqual(copy.company, self.company)
        self.assertEqual(copy.created_by, self.person)
        self.assertEqual(copy.contact, self.offer.contact)
        for field in (
            'search_started_at',
            'initial_sent_at',
            'synced_at',
            'validated_at',
        ):
            self.assertIsNone(getattr(copy, field))
        self.assertEqual(copy.sandbox_response, {})
        self.assertEqual(copy.revision, 1)
        self.assertNotIn('geo', copy.data)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.data, original)
        self.assertContains(self.client.get(self.url(offer=copy)), 'Copiée depuis')
        colleague = EmployerIdentity.objects.create(email='rh2@fiction.invalid')
        client = Client()
        self.login(client, colleague)
        self.assertEqual(client.get(self.url(offer=copy)).status_code, 404)
        EmployerMembership.objects.create(person=colleague, company=self.company)
        self.assertEqual(client.get(self.url(offer=copy)).status_code, 200)
        geo.assert_not_called()
        external.assert_not_called()

    def test_duplicate_requires_post_csrf_and_current_revision(self):
        self.assertEqual(
            self.client.get(self.url('employer_offer_duplicate')).status_code, 405
        )
        self.assertEqual(
            self.client.post(
                self.url('employer_offer_duplicate'), {'revision': 0}
            ).status_code,
            409,
        )
        self.assertFalse(
            EmployerImport.objects.filter(duplicated_from=self.offer).exists()
        )
        client = Client(enforce_csrf_checks=True)
        self.login(client, self.person)
        for action in ('employer_offer_duplicate', 'employer_offer_edit'):
            self.assertEqual(
                client.post(self.url(action), self.payload()).status_code, 403
            )

    def test_private_drafts_never_shared_and_resume_owned_only(self):
        private = self.make_offer(None, 'Private fictional draft')
        self.assertContains(
            self.client.get('/employer/offers/'), 'Private fictional draft'
        )
        self.assertEqual(self.client.get(self.url(offer=private)).status_code, 404)
        colleague = EmployerIdentity.objects.create(email='rh2@fiction.invalid')
        client = Client()
        self.login(client, colleague)
        EmployerMembership.objects.create(person=colleague, company=self.company)
        self.assertNotContains(
            client.get('/employer/offers/'), 'Private fictional draft'
        )
        self.assertEqual(
            client.post(self.url('employer_resume_attachment', private)).status_code,
            404,
        )
        self.assertRedirects(
            self.client.post(self.url('employer_resume_attachment', private)),
            '/employer/connected/',
        )
        self.assertEqual(self.client.session['employer_claim_import'], str(private.pk))

    def test_languages_and_pagination(self):
        for lang, text in [
            ('fr', 'Offres de vos établissements'),
            ('en', 'Offers from your establishments'),
            ('de', 'Angebote Ihrer Betriebsstätten'),
        ]:
            self.assertContains(self.client.get('/employer/offers/?lang=' + lang), text)
        for index in range(22):
            self.make_offer(self.company, 'Fictional ' + str(index))
        self.assertEqual(
            len(self.client.get('/employer/offers/').context['offers']), 20
        )
        self.assertEqual(
            len(self.client.get('/employer/offers/?page=2').context['offers']), 3
        )

    def test_connected_home_contains_offer_table_and_account(self):
        response = self.client.get('/employer/connected/')
        self.assertContains(response, '<table class="offer-table">', html=False)
        self.assertContains(response, self.offer.data['title'])
        self.assertNotContains(response, self.foreign.data['title'])
        self.assertContains(response, self.person.email)
        self.assertContains(response, 'Mon compte')
        self.assertContains(response, '/employer/logout/')
        self.assertNotContains(response, 'Votre adresse email est vérifiée')
        self.assertContains(response, 'scope="col"')
        self.assertContains(response, 'tabindex="0"')
