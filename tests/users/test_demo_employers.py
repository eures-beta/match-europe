from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.employers.models import EmployerProfile, JobOffer
from eures_beta.invitations.models import Invitation
from eures_beta.introductions.models import (
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
    CandidateOfferReview,
    CandidateProfileSharing,
)
from eures_beta.introductions.offer_review_services import review_state
from eures_beta.users.demo_employers import (
    LEGACY_EMPLOYER_EMAIL,
    consolidate_employers,
)
from eures_beta.users.models import User
from eures_beta.users.test_accounts import account_specs, prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='preview',
    EMAIL_DELIVERY_ENABLED=False,
)
class DemoEmployerConsolidationTests(TestCase):
    def setUp(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        self.employer = prepared_user('employer')

    def legacy_employer(self, **values):
        return User.objects.create_user(
            email=LEGACY_EMPLOYER_EMAIL, kind='employer', **values
        )

    def test_fresh_demo_has_one_employer_with_all_three_offers(self):
        self.assertEqual(User.objects.filter(kind='employer').count(), 1)
        self.assertEqual(JobOffer.objects.count(), 3)
        self.assertFalse(JobOffer.objects.exclude(employer=self.employer).exists())
        self.assertEqual(User.objects.filter(kind='candidate').count(), 5)
        self.assertEqual(len(account_specs()), 6)

    def test_existing_content_consent_and_author_history_are_preserved(self):
        legacy = self.legacy_employer(first_name='Fictional employer')
        review = CandidateOfferReview.objects.select_related('match__offer').get()
        offer = review.match.offer
        JobOffer.objects.filter(pk=offer.pk).update(employer=legacy)
        conversation = CandidateOfferConversation.objects.create(
            offer_review=review,
            employer=legacy,
            candidate=review.match.candidate.user,
            adviser=prepared_user('adviser'),
            introduction='An introduction entered during an earlier trial',
            state='open',
            employer_read=23,
        )
        message = CandidateOfferConversationMessage.objects.create(
            conversation=conversation, author=legacy, body='Existing employer reply'
        )
        invitation = Invitation.objects.create(
            email=legacy.email,
            sender_adviser=prepared_user('adviser'),
            recipient=legacy,
            accepted_at=timezone.now(),
        )
        profile = EmployerProfile.objects.create(
            user=legacy, response_coverage='all', response_time='under_week'
        )
        offer_snapshot = JobOffer.objects.values().get(pk=offer.pk)
        answer_snapshot = list(review.answers.values())
        before_fingerprint = review_state(review)['fingerprint']
        sharing = CandidateProfileSharing.objects.create(
            review=review, fingerprint=before_fingerprint, agreed=True
        )
        invitation_snapshot = Invitation.objects.values().get(pk=invitation.pk)
        invitation_snapshot['recipient_id'] = self.employer.pk
        self.client.force_login(legacy)

        consolidate_employers()
        consolidate_employers()
        offer_snapshot['employer_id'] = self.employer.pk
        self.assertEqual(JobOffer.objects.values().get(pk=offer.pk), offer_snapshot)
        self.assertEqual(list(review.answers.values()), answer_snapshot)
        review.refresh_from_db()
        self.assertEqual(review_state(review)['fingerprint'], before_fingerprint)
        sharing.refresh_from_db()
        self.assertTrue(sharing.agreed)
        self.assertEqual(sharing.fingerprint, before_fingerprint)
        conversation.refresh_from_db()
        self.assertEqual(conversation.employer_id, self.employer.pk)
        self.assertEqual(conversation.employer_read, 23)
        message.refresh_from_db()
        self.assertEqual(message.author_id, self.employer.pk)
        self.assertEqual(message.body, 'Existing employer reply')
        invitation.refresh_from_db()
        self.assertEqual(invitation.recipient_id, self.employer.pk)
        self.assertEqual(invitation.email, LEGACY_EMPLOYER_EMAIL)
        self.assertEqual(
            Invitation.objects.values().get(pk=invitation.pk), invitation_snapshot
        )
        profile.refresh_from_db()
        self.assertEqual(profile.user_id, self.employer.pk)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.first_name, 'Fictional employer')
        self.assertFalse(User.objects.filter(pk=legacy.pk).exists())
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_anonymous)
        self.assertEqual(
            self.client.post(
                reverse('test_account_sign_in'), {'account': 'matching-employer'}
            ).status_code,
            404,
        )

    def test_current_preferences_win_and_redundant_profile_is_deleted(self):
        legacy = self.legacy_employer(first_name='Earlier trial')
        self.employer.first_name = 'Current trial'
        self.employer.save(update_fields=['first_name'])
        current = EmployerProfile.objects.create(
            user=self.employer, response_coverage='selected', response_time='variable'
        )
        previous = EmployerProfile.objects.create(
            user=legacy, response_coverage='all', response_time='under_week'
        )
        consolidate_employers()
        current.refresh_from_db()
        self.assertFalse(EmployerProfile.objects.filter(pk=previous.pk).exists())
        self.assertFalse(User.objects.filter(email=LEGACY_EMPLOYER_EMAIL).exists())
        self.assertEqual(current.user_id, self.employer.pk)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.first_name, 'Current trial')

    def test_unexpected_identity_rolls_back_before_moving_offers(self):
        legacy = self.legacy_employer(is_staff=True)
        offer = JobOffer.objects.first()
        JobOffer.objects.filter(pk=offer.pk).update(employer=legacy)
        with self.assertRaises(CommandError):
            consolidate_employers()
        offer.refresh_from_db()
        legacy.refresh_from_db()
        self.assertEqual(offer.employer_id, legacy.pk)
        self.assertTrue(legacy.is_active)

    def test_production_and_nonfictional_databases_refuse_consolidation(self):
        legacy = self.legacy_employer()
        for settings in (
            {'DJANGO_ENVIRONMENT': 'production'},
            {'EMAIL_DELIVERY_ENABLED': True},
            {'DEMO_ACCOUNTS_ENABLED': False},
        ):
            with self.subTest(settings=settings), self.settings(**settings):
                with self.assertRaises(CommandError):
                    consolidate_employers()
        User.objects.create_user(email='ordinary@example.org', kind='employer')
        with self.assertRaises(CommandError):
            consolidate_employers()
        legacy.refresh_from_db()
        self.assertTrue(legacy.is_active)
