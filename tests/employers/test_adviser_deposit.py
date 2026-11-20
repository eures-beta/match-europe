import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.employers.models import Company, CompanyMembership, JobOffer
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
        self.company = Company.objects.create(name='Existing establishment')
        CompanyMembership.objects.create(company=self.company, user=self.employer)
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
            reverse('adviser_offers'), {'company_name': 'New establishment', **values}
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

    def test_no_account_is_created_and_offer_is_confirmed_and_matchable(self):
        self.setup_deposit()
        with (
            patch(
                'eures_beta.matching.services.calculate_for_saved_offer'
            ) as calculation,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.deposit()
        self.assertEqual(response.status_code, 201, response.content)
        offer = JobOffer.objects.get()
        self.assertEqual(offer.created_by, self.adviser)
        self.assertEqual(offer.adviser, self.adviser)
        self.assertEqual(offer.email, self.contact['email'])
        self.assertEqual(offer.data['companyName'], 'New establishment')
        self.assertEqual(offer.phone_recorded_by, self.adviser)
        self.assertEqual(offer.phone_confirmed_revision, offer.revision)
        self.assertIsNotNone(offer.phone_recorded_at)
        self.assertIsNone(offer.employer_contact)
        self.assertEqual(User.objects.count(), 3)
        self.assertFalse(
            CompanyMembership.objects.filter(company=offer.company).exists()
        )
        self.assertIn(offer, access.matchable_offers())
        self.assertEqual(calculation.call_count, 1)
        self.assertEqual(str(calculation.call_args.args[0]), str(offer.pk))
        self.assertEqual(calculation.call_args.args[1], offer.revision)
        self.assertContains(self.client.get(response.json()['login_url']), 'Cook')
        self.assertContains(self.client.get(reverse('adviser_offers')), 'Cook')

    def test_existing_account_and_workspace_share_the_same_offer(self):
        self.setup_deposit(company=self.company.pk, employer=self.employer.pk)
        response = self.deposit()
        self.assertEqual(response.status_code, 201)
        offer = JobOffer.objects.get()
        self.assertEqual(offer.company, self.company)
        self.assertEqual(offer.employer_contact, self.employer)
        self.client.force_login(self.employer)
        dashboard = self.client.get(reverse('dashboard'), {'lang': 'en'})
        self.assertContains(dashboard, 'Deposited by your adviser')
        self.assertContains(dashboard, reverse('employer_offer', args=[offer.pk]))
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 200
        )

    def test_explicit_new_workspace_grant_to_an_existing_account(self):
        self.setup_deposit(employer=self.employer.pk)
        self.assertEqual(self.deposit().status_code, 201)
        offer = JobOffer.objects.get()
        self.assertTrue(
            CompanyMembership.objects.filter(
                company=offer.company, user=self.employer, active=True
            ).exists()
        )

    def test_wrong_member_inactive_member_and_missing_selection_are_rejected(self):
        stranger = User.objects.create_user('stranger@sample.example', kind='employer')
        for employer in (stranger.pk, ''):
            response = self.setup_deposit(company=self.company.pk, employer=employer)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        CompanyMembership.objects.filter(company=self.company).update(active=False)
        response = self.setup_deposit(
            company=self.company.pk, employer=self.employer.pk
        )
        self.assertTrue(response.context['form'].errors)

    def test_membership_is_rechecked_at_save(self):
        self.setup_deposit(company=self.company.pk, employer=self.employer.pk)
        CompanyMembership.objects.filter(company=self.company).update(active=False)
        self.assertEqual(self.deposit().status_code, 403)
        self.assertFalse(JobOffer.objects.exists())

    def test_confirmation_required_past_or_today_only_and_no_partial_writes(self):
        self.setup_deposit()
        for values in (
            {'phone_confirmed': ''},
            {'confirmed_on': ''},
            {'confirmed_on': (timezone.localdate() + timedelta(days=1)).isoformat()},
        ):
            self.assertEqual(self.deposit(**values).status_code, 400)
            self.assertFalse(JobOffer.objects.exists())
            self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(
            self.deposit(data=json.dumps({'title': 'Incomplete'})).status_code, 400
        )

    def test_no_access_by_contact_email_and_no_account_inference(self):
        self.setup_deposit()
        contact = {**self.contact, 'email': self.employer.email}
        self.assertEqual(self.deposit(contact=json.dumps(contact)).status_code, 201)
        offer = JobOffer.objects.get()
        self.client.force_login(self.employer)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Cook')
        self.assertEqual(
            self.client.get(reverse('employer_offer', args=[offer.pk])).status_code, 404
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

    def test_later_invitation_retrieves_existing_offer_without_duplication(self):
        self.setup_deposit()
        self.deposit()
        offer = JobOffer.objects.get()
        invitation = create_invitation(
            self.adviser, 'new-employer@sample.example', 'fr', company=offer.company
        )
        visitor = Client()
        visitor.get(
            reverse('invitation_confirm'), {'invitation': invitation_token(invitation)}
        )
        visitor.post(reverse('invitation_confirm'))
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertTrue(
            CompanyMembership.objects.filter(
                company=offer.company, user=invitation.recipient
            ).exists()
        )
        offer.refresh_from_db()
        self.assertEqual(offer.employer_contact, invitation.recipient)
        self.assertEqual(offer.created_by, self.adviser)
        self.assertEqual(JobOffer.objects.count(), 1)
        self.assertContains(visitor.get(reverse('dashboard')), 'Cook')

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

    def test_cannot_grant_workspace_to_a_candidate_invitation(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            create_invitation(
                self.adviser,
                'new@sample.example',
                'fr',
                company=self.company,
                recipient_kind=Invitation.RecipientKind.CANDIDATE,
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

    def test_old_tab_cannot_use_a_new_deposits_establishment(self):
        self.setup_deposit()
        old = self.client.session['adviser_offer_setup']['offer_id']
        self.setup_deposit(company_name='Second establishment')
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
                self.setup_deposit(company_name=environment)
                self.assertEqual(self.deposit().status_code, 201)

    def test_deactivated_contact_is_rejected_at_save(self):
        self.setup_deposit(company=self.company.pk, employer=self.employer.pk)
        self.employer.is_active = False
        self.employer.save(update_fields=['is_active'])
        self.assertEqual(self.deposit().status_code, 403)
        self.assertFalse(JobOffer.objects.exists())
