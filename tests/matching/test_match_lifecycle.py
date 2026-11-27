from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.matching import (
    match_lifecycle as life,
    match_followup,
    review_email,
)
from eures_beta.matching.models import (
    CandidateOfferMatch,
    CandidateOfferConversation,
    EmployerCandidateReview,
    MatchFollowup,
    MatchConclusion,
    MatchConclusionEvent,
)
from eures_beta.users.models import User
from . import test_review_workflow as workflow_fixtures


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class MatchLifeLineTests(TestCase):
    setUpTestData = classmethod(
        workflow_fixtures.ReviewWorkflowTests.setUpTestData.__func__
    )
    finish = workflow_fixtures.ReviewWorkflowTests.finish
    handle = workflow_fixtures.ReviewWorkflowTests.handle

    def setUp(self):
        workflow_fixtures.ReviewWorkflowTests.setUp(self)
        self.life_url = reverse('adviser_match_lifecycle', args=[self.match.pk])

    def current(self, match=None):
        return life.summary(life.matches().get(pk=(match or self.match).pk))

    def open_thread(self):
        self.finish()
        self.handle('claim')
        self.handle('validated', public_message='Proceed')
        consent = EmployerCandidateReview.objects.create(
            agreement=self.current()['review'].profile_sharings.latest('pk'),
            requested_by_adviser=self.adviser,
            employer=self.match.offer.employer,
            decision='accepted',
            decided_at=timezone.now(),
            replies={'contact': 'no', 'conditions': [], 'interest': 'yes'},
        )
        response = self.client.post(
            reverse('shared_conversation_start', args=[self.review.pk]),
            {'body': 'Hello both'},
        )
        self.assertEqual(response.status_code, 302)
        return CandidateOfferConversation.objects.get(offer_review=self.review)

    def test_calculated_matching_is_visible_before_any_candidate_review(self):
        match = CandidateOfferMatch.objects.filter(
            decision='pending', candidate_offer_review__isnull=True
        ).first()
        self.assertIsNotNone(match)
        page = self.client.get(reverse('adviser_followup_list') + '?lang=en')
        self.assertContains(page, reverse('adviser_match_lifecycle', args=[match.pk]))
        item = self.current(match)
        self.assertEqual(item['action'], 'examine')
        self.assertEqual(item['steps'][0]['status'], 'done')
        self.assertEqual(item['steps'][1]['status'], 'current')
        self.assertIsNone(item['review'])
        url = reverse('adviser_match_lifecycle', args=[match.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url,
            {
                'action': 'schedule',
                'version': 0,
                'due_on': timezone.localdate().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        plan = MatchFollowup.objects.get(match=match)
        self.assertFalse(hasattr(plan, 'review_id'))
        self.assertFalse(
            match.__class__.objects.filter(
                pk=match.pk, candidate_offer_review__isnull=False
            ).exists()
        )

    def test_steps_and_actions_follow_real_replies_and_agreements(self):
        self.assertEqual(self.current()['action'], 'candidate_reminder')
        self.finish()
        self.assertEqual(self.current()['action'], 'review')
        self.handle('claim')
        self.handle('validated', public_message='Proceed')
        self.assertEqual(self.current()['action'], 'prepare_employer')
        consent = EmployerCandidateReview.objects.create(
            agreement=self.current()['review'].profile_sharings.latest('pk'),
            requested_by_adviser=self.adviser,
            employer=self.match.offer.employer,
        )
        self.assertEqual(self.current()['action'], 'employer_reminder')
        consent.decision = 'declined'
        consent.save()
        current = self.current()
        self.assertEqual(current['action'], 'review')
        self.assertFalse(current['closed'])

    def test_a_supplement_request_waits_for_the_candidate_not_the_adviser(self):
        self.finish()
        self.handle('claim')
        self.handle('clarify', public_message='Please confirm your availability.')
        current = self.current()
        self.assertEqual(current['waiting'], 'candidate')
        self.assertEqual(current['action'], 'candidate_reminder')
        self.review.refresh_from_db()
        reminders = match_followup.context(self.review)['recipients']
        self.assertEqual(reminders['candidate'][1], 'candidate_offer_confirmation')

    def test_completed_replies_without_a_sharing_decision_still_wait_for_the_candidate(
        self,
    ):
        from eures_beta.matching import offer_review_services

        for question in offer_review_services.review_state(self.review)['rows']:
            if question['askable']:
                offer_review_services.answer(
                    self.candidate,
                    self.review.pk,
                    question['key'],
                    question['fingerprint'],
                    'yes',
                )
        self.assertEqual(self.current()['waiting'], 'candidate')

    def test_declining_the_shared_thread_never_asks_for_a_new_employer_request(self):
        thread = self.open_thread()
        thread.state = 'declined'
        thread.save(update_fields=['state'])
        self.assertEqual(self.current()['action'], 'review')

    def test_employer_declaration_then_adviser_confirmation_closes_only_this_matching(
        self,
    ):
        thread = self.open_thread()
        self.assertEqual(self.current()['action'], 'conversation')
        self.assertFalse(self.current()['closed'])
        initial_messages = list(thread.messages.values_list('pk', 'body'))
        due = timezone.localdate() + timedelta(days=2)
        life.schedule(self.adviser, self.match.pk, due_on=due, version=0)
        self.client.force_login(self.match.offer.employer)
        report = reverse('report_match_hiring', args=[self.match.pk])
        self.assertContains(
            self.client.get(
                reverse('shared_conversation', args=[thread.pk]) + '?lang=en'
            ),
            'I have hired this person',
        )
        self.assertEqual(self.client.get(report).status_code, 200)
        response = self.client.post(report, {'version': 0, 'start_on': due.isoformat()})
        self.assertEqual(response.status_code, 302)
        conclusion = MatchConclusion.objects.get(match=self.match)
        self.assertEqual(conclusion.state, 'reported')
        self.assertIsNone(conclusion.confirmed_at)
        self.assertEqual(self.current()['action'], 'confirm')
        self.client.force_login(self.adviser)
        dashboard = self.client.get(reverse('dashboard') + '?lang=en')
        self.assertEqual(dashboard.context['hiring_confirmation_count'], 1)
        self.assertContains(dashboard, 'Hiring to confirm')
        self.assertFalse(self.current()['closed'])
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(
                self.life_url, {'action': 'hired', 'version': 1}
            ).status_code,
            400,
        )
        response = self.client.post(
            self.life_url,
            {
                'action': 'hired',
                'version': 1,
                'verified': 'on',
                'start_on': due.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        conclusion.refresh_from_db()
        self.assertEqual(conclusion.state, 'hired')
        self.assertEqual(conclusion.confirmed_by_adviser, self.other)
        self.assertTrue(self.current()['closed'])
        self.assertEqual(self.current()['steps'][-1]['status'], 'done')
        self.assertEqual(conclusion.events.count(), 2)
        self.assertEqual(
            self.client.get(reverse('dashboard')).context['hiring_confirmation_count'],
            0,
        )
        self.assertEqual(
            list(thread.messages.values_list('pk', 'body')), initial_messages
        )
        thread.refresh_from_db()
        self.assertEqual(thread.state, 'open')
        plan = MatchFollowup.objects.get(match=self.match)
        self.assertEqual(plan.outcome, 'hired')
        self.assertIsNone(plan.due_on)
        self.review.refresh_from_db()
        self.assertEqual(match_followup.context(self.review)['recipients'], {})
        with patch.object(review_email, 'send_mail') as send:
            self.assertFalse(review_email.send(self.review.pk, adviser=self.adviser))
            send.assert_not_called()
        self.assertContains(
            self.client.get(reverse('adviser_followup_list') + '?closed=1'),
            self.life_url,
        )
        self.assertNotContains(
            self.client.get(reverse('adviser_followup_list')), self.life_url
        )

    def test_no_hiring_without_an_open_thread_or_from_another_employer(self):
        employer = self.match.offer.employer
        with self.assertRaises(PermissionDenied):
            life.conclude(employer, self.match.pk, 'reported', 0)
        self.open_thread()
        other_employer = User.objects.create_user(
            'other-company@example.org', kind='employer'
        )
        self.client.force_login(other_employer)
        self.assertEqual(
            self.client.get(
                reverse('report_match_hiring', args=[self.match.pk])
            ).status_code,
            404,
        )
        for user in (self.candidate, self.adviser):
            with self.assertRaises(PermissionDenied):
                life.conclude(user, self.match.pk, 'reported', 0)
        with self.assertRaises(ValidationError):
            life.conclude(self.adviser, self.match.pk, 'hired', 0, verified=True)

    def test_double_submissions_and_stale_check_ins_do_not_overwrite_history(self):
        self.open_thread()
        employer = self.match.offer.employer
        life.conclude(employer, self.match.pk, 'reported', 0)
        with self.assertRaises(life.Changed):
            life.conclude(employer, self.match.pk, 'reported', 0)
        self.assertEqual(MatchConclusionEvent.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            life.conclude(employer, self.match.pk, 'hired', 1, verified=True)
        life.conclude(self.adviser, self.match.pk, 'hired', 1, verified=True)
        with self.assertRaises(life.Changed):
            life.conclude(self.other, self.match.pk, 'stopped', 1, reason='Stale form')
        self.assertEqual(MatchConclusionEvent.objects.count(), 2)

    def test_negative_closure_requires_a_reason_and_keeps_candidate_data(self):
        initial = self.match.candidate.desired_countries
        with self.assertRaises(ValidationError):
            life.conclude(self.adviser, self.match.pk, 'stopped', 0)
        life.conclude(
            self.adviser,
            self.match.pk,
            'stopped',
            0,
            reason='Candidate accepted another offer.',
        )
        current = self.current()
        self.assertTrue(current['closed'])
        self.assertTrue(current['stopped'])
        self.match.candidate.refresh_from_db()
        self.assertEqual(self.match.candidate.desired_countries, initial)
        with self.assertRaises(life.Changed):
            life.schedule(
                self.adviser, self.match.pk, due_on=timezone.localdate(), version=0
            )

    def test_csrf_roles_and_all_environments_keep_the_same_controls(self):
        for user in (self.candidate, self.match.offer.employer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.life_url).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.adviser)
        self.assertEqual(
            csrf.post(
                self.life_url, {'action': 'stopped', 'version': 0, 'reason': 'No'}
            ).status_code,
            403,
        )
        self.client.force_login(self.adviser)
        for environment in ('local', 'preview', 'production'):
            with self.settings(
                DJANGO_ENVIRONMENT=environment, DEMO_ACCOUNTS_ENABLED=False
            ):
                for language in ('fr', 'en', 'de'):
                    page = self.client.get(
                        self.life_url + '?lang=' + language, REMOTE_ADDR='203.0.113.8'
                    )
                    self.assertEqual(page.status_code, 200)
                    self.assertContains(page, 'matching-lifeline')

    def test_database_enforces_conclusion_roles(self):
        self.open_thread()
        obj = life.conclude(self.match.offer.employer, self.match.pk, 'reported', 0)
        with self.assertRaises(DatabaseError), transaction.atomic():
            MatchConclusion.objects.filter(pk=obj.pk).update(
                declared_by_employer=self.adviser
            )

    def test_reminder_does_not_require_manually_inventing_a_plan_first(self):
        self.review.refresh_from_db()
        current = match_followup.context(self.review)
        self.assertIsNone(current['plan'])
        event = match_followup.reminder(
            self.adviser, self.review.pk, current['stamp'], 'candidate', 'Please reply'
        )
        self.assertEqual(event.delivery_status, 'disabled')
        plan = MatchFollowup.objects.get(match=self.match)
        self.assertIsNone(plan.due_on)

    def test_matching_and_employer_links_are_preserved_after_sign_in(self):
        from eures_beta.www.accounts.return_path import canonical_destination

        for route, pk in (
            ('adviser_match_lifecycle', self.match.pk),
            ('report_match_hiring', self.match.pk),
            ('shared_conversation', 1),
            ('respond_employer_consent', 1),
        ):
            destination = reverse(route, args=[pk]) + '?lang=de'
            self.assertEqual(canonical_destination(destination), destination)
        for unsafe in (
            'https://attacker.invalid/',
            '//attacker.invalid/',
            self.life_url + '?other=bad',
            self.life_url + '#fragment',
        ):
            self.assertEqual(canonical_destination(unsafe), '')
