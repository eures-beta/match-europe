import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.employers.models import JobOffer
from eures_beta.invitations.models import Invitation
from eures_beta.invitations.services import create_invitation, invitation_token
from eures_beta.matching import access
from eures_beta.users.models import User


class AdviserDepositTests(TestCase):
    def setUp(self):
        self.adviser = User.objects.create_user(
            'adviser@sample.example', kind='adviser'
        )
        self.employer = User.objects.create_user(
            'employer@sample.example', kind='employer'
        )
        self.other = User.objects.create_user('other@sample.example', kind='adviser')
        self.client.force_login(self.adviser)
        self.data = dict(
            title='Cook',
            companyName='Untrusted name',
            city='Metz',
            description='Prepare meals',
            contractType='PERMANENT_CONTRACT',
        )
        self.contact = dict(
            name='Employer Contact',
            email='contact@sample.example',
            phone='',
            function='',
        )

    def setup_deposit(self, **values):
        return self.client.post(
            reverse('adviser_offers'), {'email': self.contact['email'], **values}
        )

    def deposit(self, **values):
        payload = dict(
            kind='manual',
            text='Cook job',
            agreement='true',
            language='fr',
            data=json.dumps(self.data),
            contact=json.dumps(self.contact),
            phone_confirmed='true',
            confirmed_on=timezone.localdate().isoformat(),
        )
        return self.client.post(
            reverse('adviser_offer_deposits'),
            {**payload, **values},
            HTTP_X_DEPOSIT_TOKEN=self.client.session.get('adviser_offer_setup', {}).get(
                'offer_id', ''
            ),
        )

    def test_confirmation_required_past_or_today_only_and_no_partial_writes(self):
        self.setup_deposit()
        for values in (
            {'phone_confirmed': ''},
            {'confirmed_on': ''},
            {'confirmed_on': (timezone.localdate() + timedelta(days=1)).isoformat()},
        ):
            self.assertEqual(self.deposit(**values).status_code, 400)
            self.assertFalse(JobOffer.objects.exists())
            self.assertEqual(User.objects.count(), 3)
        self.assertEqual(
            self.deposit(data=json.dumps({'title': 'Incomplete'})).status_code, 400
        )

    def test_only_active_advisers_can_use_the_flow(self):
        candidate = User.objects.create_user(
            'candidate@sample.example', kind='candidate'
        )
        for user in (None, self.employer, candidate):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for name in (
                'adviser_offers',
                'adviser_offer_import',
                'adviser_offer_deposits',
            ):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
            self.assertEqual(
                self.client.post(reverse('adviser_offer_source')).status_code, 403
            )

    def test_csrf_and_missing_or_expired_setup(self):
        self.assertEqual(self.deposit().status_code, 409)
        self.setup_deposit()
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.adviser)
        self.assertEqual(
            csrf.post(
                reverse('adviser_offers'), {'company_name': 'Forbidden'}
            ).status_code,
            403,
        )
        self.assertEqual(
            csrf.post(reverse('adviser_offer_deposits'), {}).status_code, 403
        )
        session = self.client.session
        session['adviser_offer_setup']['at'] = 0
        session.save()
        self.assertEqual(self.deposit().status_code, 409)

    @override_settings(ALBERT_SIMULATED=True)
    def test_shared_source_reader_and_three_language_import(self):
        self.setup_deposit()
        for language in ('fr', 'en', 'de'):
            page = self.client.get(reverse('adviser_offer_import'), {'lang': language})
            self.assertContains(page, 'data-adviser-deposit="true"')
            self.assertContains(page, 'name="confirmed_on"')
            self.assertNotContains(page, 'id="employer-profile"')
        response = self.client.post(
            reverse('adviser_offer_source'),
            {'kind': 'manual', 'text': 'Cook in Metz', 'agreement': 'true'},
            HTTP_X_DEPOSIT_TOKEN=self.client.session['adviser_offer_setup']['offer_id'],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['kind'], 'manual')
        self.assertEqual(
            self.client.post(
                reverse('job_offer_source'), {'kind': 'manual'}
            ).status_code,
            403,
        )

    def test_changed_revision_needs_new_confirmation_and_other_adviser_cannot_edit(
        self,
    ):
        self.setup_deposit()
        self.deposit()
        offer = JobOffer.objects.get()
        JobOffer.objects.filter(pk=offer.pk).update(revision=2)
        self.assertNotIn(offer, access.matchable_offers())
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse('adviser_offer', args=[offer.pk])).status_code, 404
        )

    def test_real_matching_is_calculated_without_an_employer_account(self):
        from eures_beta.candidates.models import CandidateProfile
        from eures_beta.candidates.skill_choices import skill_groups
        from eures_beta.matching.models import MatchEvaluation
        from eures_beta.skills.skills_pilot import catalogue

        user = User.objects.create_user(
            'candidate-matching@sample.example', kind='candidate'
        )
        candidate = CandidateProfile.objects.create(
            user=user,
            display_name='Fictional candidate',
            email_verified_at=timezone.now(),
            project_mode='open',
            acquired_skills=[catalogue()[0]['nettoyage']['keySkills'][0]['skillUri']],
            professional_behaviours=list(skill_groups()[0]['professional_behaviours'])[
                :3
            ],
            desired_countries=['FR'],
            mobility='discuss',
            availability='discuss',
            contract_types=['permanent'],
            working_time=['full'],
            working_conditions=['weekend'],
            language_skills={
                'status': 'specified',
                'languages': [{'code': 'fr', 'level': 'B1'}],
            },
            salary_preference='discuss',
            schedule_preference='discuss',
        )
        self.setup_deposit()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.deposit().status_code, 201)
        self.assertTrue(
            MatchEvaluation.objects.filter(
                match__candidate=candidate, match__offer=JobOffer.objects.get()
            ).exists()
        )

    def test_old_tab_cannot_use_a_new_deposit(self):
        self.setup_deposit()
        old = self.client.session['adviser_offer_setup']['offer_id']
        self.setup_deposit(email='second@sample.example')
        self.assertEqual(
            self.client.post(
                reverse('adviser_offer_deposits'), {}, HTTP_X_DEPOSIT_TOKEN=old
            ).status_code,
            409,
        )
        self.assertFalse(JobOffer.objects.exists())

    def test_edit_reconfirms_the_current_revision_and_rejects_stale_write(self):
        self.setup_deposit()
        self.deposit()
        offer = JobOffer.objects.get()
        url = reverse('adviser_offer', args=[offer.pk])
        page = self.client.get(url)
        values = {
            key: value
            for key, value in page.context['form'].initial.items()
            if key in page.context['form'].fields
        }
        values.update(
            revision=offer.revision,
            title='Updated cook',
            phone_confirmed='true',
            confirmed_on=timezone.localdate().isoformat(),
        )
        values.update({'contact-' + key: val for key, val in self.contact.items()})
        self.assertEqual(self.client.post(url, values).status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(offer.data['title'], 'Updated cook')
        self.assertEqual(offer.revision, 2)
        self.assertEqual(offer.phone_confirmed_revision, 2)
        self.assertIn(offer, access.matchable_offers())
        response = self.client.post(url, {**values, 'title': 'Stale overwrite'})
        self.assertTrue(response.context['form'].errors)
        offer.refresh_from_db()
        self.assertEqual(offer.data['title'], 'Updated cook')

    def test_deposit_has_the_same_business_rights_in_all_environments(self):
        for environment in ('local', 'preview', 'production'):
            with override_settings(
                DJANGO_ENVIRONMENT=environment,
                DEMO_ACCOUNTS_ENABLED=False,
                EMAIL_DELIVERY_ENABLED=True,
            ):
                self.setup_deposit(email=environment + '@sample.example')
                self.assertEqual(self.deposit().status_code, 201)

    def test_deposit_precreates_active_employer_and_owns_offer_without_company(self):
        self.setup_deposit()
        with (
            patch(
                'eures_beta.matching.services.calculate_for_saved_offer'
            ) as calculate,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.deposit()
        self.assertEqual(response.status_code, 201, response.content)
        offer = JobOffer.objects.get()
        employer = User.objects.get(email=self.contact['email'])
        self.assertEqual(offer.employer, employer)
        self.assertEqual(offer.adviser, self.adviser)
        self.assertNotIn('company', [f.name for f in JobOffer._meta.fields])
        self.assertEqual(employer.kind, 'employer')
        self.assertTrue(employer.is_active)
        self.assertFalse(employer.is_staff or employer.is_superuser)
        self.assertFalse(employer.has_usable_password())
        self.assertIsNone(employer.last_login)
        self.assertNotIn('email', offer.contact)
        self.assertNotIn('email', [f.name for f in JobOffer._meta.fields])
        self.assertNotIn('employer_contact', [f.name for f in JobOffer._meta.fields])
        self.assertIn(offer, access.matchable_offers())
        self.assertEqual(calculate.call_count, 1)
        from django.apps import apps

        for name in ('Company', 'CompanyMembership'):
            with self.assertRaises(LookupError):
                apps.get_model('employers', name)
        self.client.force_login(employer)
        self.assertContains(self.client.get(reverse('dashboard')), 'Cook')
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 200
        )
        self.client.force_login(self.employer)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Cook')
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 404
        )

    def test_existing_employer_is_reused_case_insensitively_and_payload_cannot_change_owner(
        self,
    ):
        self.setup_deposit(email=' EMPLOYER@sample.example ')
        response = self.deposit()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(JobOffer.objects.get().employer, self.employer)
        self.assertEqual(User.objects.count(), 3)

    def test_non_employer_or_disabled_account_blocks_setup_and_save(self):
        candidate = User.objects.create_user(
            'candidate@sample.example', kind='candidate'
        )
        for user in (self.adviser, candidate):
            response = self.setup_deposit(email=user.email)
            self.assertTrue(response.context['form'].errors)
        self.setup_deposit()
        User.objects.create_user(self.contact['email'], kind='candidate')
        self.assertEqual(self.deposit().status_code, 400)
        self.assertFalse(JobOffer.objects.exists())
        self.setup_deposit(email=self.employer.email)
        self.employer.is_active = False
        self.employer.save(update_fields=['is_active'])
        self.assertEqual(self.deposit().status_code, 400)
        self.assertFalse(JobOffer.objects.exists())
        self.employer.refresh_from_db()
        self.assertFalse(self.employer.is_active)

    @override_settings(
        LOGIN_EMAIL_ORIGIN='https://testserver',
        ALLOWED_HOSTS=['testserver'],
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_invitation_uses_standard_magic_link_and_later_login_finds_same_offer(self):
        from django.core import mail
        from urllib.parse import urlsplit, parse_qs

        self.setup_deposit()
        with (
            patch('eures_beta.users.email_login.email_ready', return_value=True),
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertEqual(self.deposit().status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.contact['email']])
        import re

        link = re.search(r'https://[^\s]+', mail.outbox[0].body).group()
        visitor = Client()
        visitor.get(urlsplit(link).path, parse_qs(urlsplit(link).query))
        self.assertNotIn('_auth_user_id', visitor.session)
        visitor.post(reverse('magic_confirm'))
        self.assertContains(visitor.get(reverse('dashboard')), 'Cook')
        self.assertEqual(JobOffer.objects.count(), 1)
        # Normal login also accepts this already-created account without registration.
        visitor.logout()
        with patch('eures_beta.www.accounts.views.email_ready', return_value=True):
            visitor.post(reverse('magic_login'), {'email': self.contact['email']})
        self.assertEqual(len(mail.outbox), 2)

    def test_failed_save_rolls_back_new_account_and_does_not_send_email(self):
        from django.core.exceptions import ValidationError

        self.setup_deposit()
        with (
            patch.object(JobOffer, 'save', side_effect=ValidationError('invalid')),
            patch('eures_beta.users.email_login.send_sign_in_link') as send,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertEqual(self.deposit().status_code, 400)
        self.assertFalse(User.objects.filter(email=self.contact['email']).exists())
        self.assertFalse(JobOffer.objects.exists())
        send.assert_not_called()
