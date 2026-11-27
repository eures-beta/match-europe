from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import DatabaseError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

from eures_beta.followup import match_followup as followup, match_lifecycle
from eures_beta.introductions import offer_review_services as answers, review_workflow
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.introductions.models import (
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
    EmployerCandidateReview,
)
from eures_beta.followup.models import MatchFollowup, MatchFollowupEvent
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class MatchFollowupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())

    def setUp(self):
        self.adviser = prepared_user('adviser')
        self.other = User.objects.create_user('colleague@example.org', kind='adviser')
        self.match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        self.match.decision = 'retained'
        self.match.save()
        self.candidate = self.match.candidate.user
        self.employer = self.match.offer.employer
        self.review = answers.request_offer_review(self.adviser, self.match.pk)
        self.url = reverse('adviser_match_lifecycle', args=[self.match.pk])
        self.match_url = reverse('adviser_match_lifecycle', args=[self.match.pk])
        self.client.force_login(self.adviser)

    def current(self):
        self.review.refresh_from_db()
        return followup.context(self.review)

    def plan(self, **changes):
        current = MatchFollowup.objects.filter(match=self.match).first()
        return match_lifecycle.schedule(
            self.adviser,
            self.match.pk,
            version=current.version if current else 0,
            **(
                dict(
                    next_action='Organiser un entretien',
                    waiting_for='candidate',
                    due_on=timezone.localdate(),
                )
                | changes
            ),
        )

    def employer_request(self):
        for row in answers.review_state(self.review)['rows']:
            if row['askable']:
                answers.answer(
                    self.candidate,
                    self.review.pk,
                    row['key'],
                    row['fingerprint'],
                    'yes',
                )
        state = answers.review_state(self.review)
        answers.agree(self.candidate, self.review.pk, state['fingerprint'], True)
        for action in ('claim', 'validated'):
            self.review.refresh_from_db()
            review_workflow.handle(
                self.adviser,
                self.review.pk,
                action,
                self.review.workflow_version,
                answers.review_state(self.review)['fingerprint'],
                public_message='Proceed',
            )
        self.review.refresh_from_db()
        return EmployerCandidateReview.objects.create(
            agreement=answers.review_state(self.review)['agreement'],
            requested_by_adviser=self.adviser,
            employer=self.employer,
        )

    def test_replaced_review_route_is_removed_and_current_navigation_remains(self):
        with self.assertRaises(NoReverseMatch):
            reverse('adviser_followup', args=[self.review.pk])
        self.assertEqual(
            self.client.get(
                '/matching/follow-up/' + str(self.review.pk) + '/'
            ).status_code,
            404,
        )
        self.assertContains(
            self.client.get(reverse('adviser_followup_list')), self.match_url
        )

    def test_get_never_creates_a_plan_and_shared_adviser_can_update(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(MatchFollowup.objects.count(), 0)
        plan = self.plan()
        self.client.force_login(self.other)
        page = self.client.get(self.url)
        data = dict(
            page.context['schedule_form'].initial,
            due_on=timezone.localdate() + timedelta(days=2),
        )
        self.assertEqual(
            self.client.post(self.url, dict(data, action='schedule')).status_code, 302
        )
        plan.refresh_from_db()
        self.assertEqual(plan.updated_by_adviser, self.other)
        self.assertEqual(plan.events.count(), 2)

    def test_stale_plan_and_double_reminder_do_not_overwrite_or_send_twice(self):
        self.plan()
        stamp = self.current()['stamp']
        event = followup.reminder(
            self.other, self.review.pk, stamp, 'candidate', 'Please reply'
        )
        self.assertEqual(event.delivery_status, 'disabled')
        with self.assertRaises(followup.Changed):
            followup.reminder(
                self.adviser, self.review.pk, stamp, 'candidate', 'Please reply'
            )
        with self.assertRaises(followup.RetryLater):
            followup.reminder(
                self.adviser,
                self.review.pk,
                self.current()['stamp'],
                'candidate',
                'Please reply',
            )
        self.assertEqual(
            MatchFollowupEvent.objects.filter(action='reminder').count(), 1
        )

    def test_email_is_single_recipient_and_has_no_private_plan_or_tokens_in_history(
        self,
    ):
        self.plan(next_action='INTERNAL_PRIVATE_PLAN')
        with self.settings(
            DEMO_ACCOUNTS_ENABLED=False,
            EMAIL_DELIVERY_ENABLED=True,
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            EMAIL_HOST='smtp.example.invalid',
            DEFAULT_FROM_EMAIL='no-reply@example.org',
            LOGIN_EMAIL_ORIGIN='https://testserver',
        ):
            event = followup.reminder(
                self.adviser,
                self.review.pk,
                self.current()['stamp'],
                'candidate',
                'Votre retour nous aiderait.',
            )
        self.assertEqual(event.delivery_status, 'sent')
        self.assertEqual(mail.outbox[-1].to, [self.candidate.email])
        self.assertNotIn('INTERNAL_PRIVATE_PLAN', mail.outbox[-1].body)
        self.assertIn(reverse('magic_confirm'), mail.outbox[-1].body)
        from tests.emails.assertions import assert_clickable_email

        assert_clickable_email(self, mail.outbox[-1])
        self.assertNotIn('sesame', event.message + str(event.snapshot))

    def test_transport_failure_is_recorded_without_silent_retry(self):
        self.plan()
        with (
            patch.object(followup, 'email_ready', return_value=True),
            patch.object(followup, 'send_mail', side_effect=RuntimeError('secret')),
        ):
            event = followup.reminder(
                self.adviser,
                self.review.pk,
                self.current()['stamp'],
                'candidate',
                'Please reply',
            )
        self.assertEqual(event.delivery_status, 'failed')
        self.assertNotIn('secret', str(event.snapshot))

    def test_employer_reminder_requires_a_current_pending_request(self):
        self.plan()
        self.assertNotIn('employer', self.current()['recipients'])
        consent = self.employer_request()
        current = self.current()
        self.assertEqual(list(current['recipients']), ['employer'])
        event = followup.reminder(
            self.other, self.review.pk, current['stamp'], 'employer', 'Please review'
        )
        self.assertEqual(event.recipient, 'employer')
        consent.decision = 'declined'
        consent.save()
        self.assertEqual(self.current()['recipients'], {})

    def test_offer_change_and_withdrawal_block_employer_relance(self):
        self.employer_request()
        self.plan()
        stamp = self.current()['stamp']
        self.match.offer.data['title'] = 'Changed title'
        self.match.offer.save()
        self.assertNotIn('employer', self.current()['recipients'])
        with self.assertRaises(followup.Changed):
            followup.reminder(
                self.adviser, self.review.pk, stamp, 'employer', 'Please reply'
            )

    def test_open_thread_allows_each_party_and_new_reply_invalidates_preview(self):
        consent = self.employer_request()
        consent.decision, consent.decided_at = 'accepted', timezone.now()
        consent.replies = {'contact': 'no', 'conditions': [], 'interest': 'yes'}
        consent.save()
        response = self.client.post(
            reverse('shared_conversation_start', args=[self.review.pk]),
            {'body': 'Hello both'},
        )
        self.assertEqual(response.status_code, 302)
        self.plan()
        current = self.current()
        self.assertEqual(set(current['recipients']), {'candidate', 'employer'})
        thread = CandidateOfferConversation.objects.get(offer_review=self.review)
        CandidateOfferConversationMessage.objects.create(
            conversation=thread, author=self.employer, body='Tomorrow?'
        )
        with self.assertRaises(followup.Changed):
            followup.reminder(
                self.adviser,
                self.review.pk,
                current['stamp'],
                'employer',
                'Please reply',
            )

    def test_closing_is_explicit_and_keeps_agreements_and_messages(self):
        self.plan()
        match_lifecycle.conclude(
            self.adviser,
            self.match.pk,
            'stopped',
            0,
            reason='The candidate accepted another offer.',
        )
        current = self.current()
        self.assertFalse(current['due'])
        self.assertEqual(current['recipients'], {})
        self.assertIsNone(current['plan'].due_on)
        self.match.refresh_from_db()
        self.assertEqual(self.match.decision, 'retained')
        self.assertNotContains(
            self.client.get(reverse('adviser_followup_list')), self.match_url
        )
        self.assertContains(
            self.client.get(reverse('adviser_followup_list') + '?closed=1'),
            self.match_url,
        )
        response = self.client.post(
            self.url,
            {
                'action': 'plan',
                'stamp': current['stamp'],
                'outcome': 'hired',
                'waiting_for': 'adviser',
                'next_action': 'Close',
                'closure_reason': '',
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_all_other_roles_and_csrf_are_refused(self):
        for user in (self.candidate, self.employer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            with self.assertRaises(PermissionDenied):
                followup.reminder(user, self.review.pk, '', 'candidate', 'Hello')
        self.adviser.is_active = False
        self.adviser.save()
        self.client.force_login(self.adviser)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        with self.assertRaises(PermissionDenied):
            followup.reminder(self.adviser, self.review.pk, '', 'candidate', 'Hello')
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.other)
        self.assertEqual(csrf.post(self.url, {'action': 'plan'}).status_code, 403)

    def test_database_refuses_non_adviser_authors(self):
        plan = self.plan()
        with self.assertRaises(DatabaseError), transaction.atomic():
            MatchFollowup.objects.filter(pk=plan.pk).update(
                updated_by_adviser=self.candidate
            )

    def test_languages_and_remote_environments(self):
        self.plan()
        for environment in ('local', 'preview', 'production'):
            with self.settings(
                DJANGO_ENVIRONMENT=environment, DEMO_ACCOUNTS_ENABLED=False
            ):
                for language in ('fr', 'en', 'de'):
                    response = self.client.get(
                        self.url + '?lang=' + language, REMOTE_ADDR='203.0.113.7'
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'Organiser un entretien')

    def test_due_alert_and_future_date(self):
        self.plan(due_on=timezone.localdate() + timedelta(days=7))
        page = self.client.get(reverse('dashboard'))
        self.assertEqual(page.context['followup_due_count'], 0)
        self.plan()
        page = self.client.get(reverse('dashboard'))
        self.assertEqual(page.context['followup_due_count'], 1)
        self.assertContains(
            self.client.get(reverse('adviser_followup_list') + '?due=1'), self.match_url
        )
        self.plan(due_on=timezone.localdate() + timedelta(days=1))
        self.assertNotContains(
            self.client.get(reverse('adviser_followup_list') + '?due=1'), self.match_url
        )

    def test_reminder_and_rescheduling_keep_the_original_waiting_date(self):
        plan = self.plan()
        original = self.current()['waiting_since']
        self.plan(due_on=timezone.localdate() + timedelta(days=2))
        followup.reminder(
            self.adviser,
            self.review.pk,
            self.current()['stamp'],
            'candidate',
            'Please reply',
        )
        self.assertEqual(self.current()['waiting_since'], original)
        self.plan(next_action='Ask for availability')
        self.assertGreater(self.current()['waiting_since'], original)

    def test_withdrawn_candidate_permission_blocks_employer_reminders(self):
        self.employer_request()
        self.plan()
        state = answers.review_state(self.review)
        stamp = self.current()['stamp']
        answers.agree(
            self.candidate,
            self.review.pk,
            state['fingerprint'],
            False,
            previous=state['agreement'].pk,
        )
        self.assertNotIn('employer', self.current()['recipients'])
        with self.assertRaises(followup.Changed):
            followup.reminder(
                self.adviser, self.review.pk, stamp, 'employer', 'Please reply'
            )

    def test_previewed_reminder_submission_records_actual_delivery_result(self):
        self.plan()
        page = self.client.get(self.url + '?lang=fr')
        data = dict(
            page.context['reminder_form'].initial,
            action='reminder',
            message='Pouvez-vous répondre ?',
        )
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        event = MatchFollowupEvent.objects.get(action='reminder')
        self.assertEqual(event.delivery_status, 'disabled')
        self.assertContains(response, 'Pouvez-vous répondre ?')

    def test_dashboard_puts_overdue_dossiers_first_and_explains_the_delay(self):
        self.plan(due_on=timezone.localdate() - timedelta(days=2))
        response = self.client.get(reverse('adviser_followup_list') + '?lang=fr')
        self.assertEqual(response.context['rows'][0]['review'].pk, self.review.pk)
        self.assertFalse(response.context['due_only'])
        self.assertContains(response, 'Suivi en retard de 2 jours')
        self.assertContains(response, 'Préparer la relance du candidat')
        self.assertEqual(response.context['counts']['due'], 1)
        self.assertContains(response, self.match_url)

    def test_unplanned_and_future_filters_and_guided_plan_form(self):
        index = reverse('adviser_followup_list')
        self.assertContains(
            self.client.get(index + '?filter=unplanned'), self.match_url
        )
        page = self.client.get(self.url + '?lang=fr')
        self.assertEqual(
            page.context['schedule_form'].initial['due_on'],
            None,
        )
        self.assertContains(
            page, 'À quelle date souhaitez-vous refaire le point sur ce matching ?'
        )
        self.plan(due_on=timezone.localdate() + timedelta(days=3))
        self.assertNotContains(
            self.client.get(index + '?filter=unplanned'), self.match_url
        )
        self.assertContains(
            self.client.get(index + '?filter=upcoming&lang=fr'),
            'Prochain point dans 3 jours',
        )
        self.assertContains(self.client.get(index + '?filter=upcoming'), self.match_url)

    def test_today_and_disabled_delivery_are_explicit_in_the_dossier(self):
        self.plan()
        response = self.client.get(self.url + '?lang=fr')
        self.assertEqual(
            response.context['dossier']['date_status'], 'À suivre aujourd’hui'
        )
        self.assertContains(response, 'aucun email ne sera envoyé')
        self.assertContains(response, 'Enregistrer cette relance sans envoi')
        self.assertNotContains(response, 'Envoyer cette relance par email')
