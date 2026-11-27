from copy import copy
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import (
    offer_review_services as answers,
    review_workflow as workflow,
    services,
)
from eures_beta.candidates.models import CandidateProfileReviewSuggestion
from eures_beta.matching.models import (
    CandidateOfferMatch,
    CandidateOfferReview,
    EmployerCandidateReview,
)
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class ReviewWorkflowTests(TestCase):
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
        self.review = answers.request_offer_review(self.adviser, self.match.pk)
        self.url = reverse('adviser_conversation', args=[self.review.pk])
        self.client.force_login(self.adviser)

    def finish(self, agreed=True):
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
        answers.agree(self.candidate, self.review.pk, state['fingerprint'], agreed)
        self.review.refresh_from_db()

    def handle(self, action, user=None, **kwargs):
        self.review.refresh_from_db()
        return workflow.handle(
            user or self.adviser,
            self.review.pk,
            action,
            self.review.workflow_version,
            answers.review_state(self.review)['fingerprint'],
            **kwargs,
        )

    def test_completion_keeps_review_visible_and_saves_immutable_summary(self):
        self.finish()
        self.assertEqual(self.review.workflow_state, 'ready')
        self.assertTrue(self.review.summary['sharing'])
        event = self.review.events.get(action='submitted')
        self.assertEqual(event.snapshot, self.review.summary)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.force_login(self.other)
        self.assertContains(
            self.client.get(reverse('dashboard') + '?view=conversations'), self.url
        )
        self.assertEqual(self.client.get(self.url).status_code, 200)
        # GET neither claims the review nor backfills legacy data.
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_version, 1)
        workflow.submit(
            self.candidate,
            self.review.pk,
            answers.review_state(self.review)['fingerprint'],
            self.review.workflow_version,
        )
        self.assertEqual(self.review.events.filter(action='submitted').count(), 1)

    def test_refused_permission_is_still_visible_and_cannot_validate(self):
        self.finish(False)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.handle('claim')
        with self.assertRaises(ValidationError):
            self.handle('validated', public_message='Proceed')
        self.handle(
            'refused',
            public_message='This opportunity requires sharing. Other opportunities remain possible.',
        )
        self.assertEqual(self.client.get(self.url).status_code, 200)

        from eures_beta.matching import review_email

        with (
            patch('eures_beta.matching.review_email.email_ready', return_value=True),
            patch('eures_beta.matching.review_email.send_mail', return_value=1) as send,
        ):
            self.assertFalse(review_email.send(self.review.pk, adviser=self.adviser))
            send.assert_not_called()
        self.assertFalse(self.client.get(self.url).context['can_resend'])

    def test_claim_takeover_and_decision_are_versioned(self):
        self.finish()
        old_version = self.review.workflow_version
        fingerprint = answers.review_state(self.review)['fingerprint']
        self.handle('claim')
        with self.assertRaises(services.StaleEvaluation):
            workflow.handle(
                self.other, self.review.pk, 'claim', old_version, fingerprint
            )
        with self.assertRaises(PermissionDenied):
            self.handle('refused', self.other, public_message='No')
        with self.assertRaises(services.StaleEvaluation):
            self.handle('takeover', self.other)
        self.handle('takeover', self.other, internal_note='Covering an absence')
        self.handle(
            'validated',
            self.other,
            public_message='We can proceed with this opportunity.',
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.assigned_to_adviser, self.other)
        self.assertEqual(
            list(self.review.events.values_list('action', flat=True)),
            ['submitted', 'claim', 'takeover', 'validated'],
        )
        from django.utils import timezone

        EmployerCandidateReview.objects.create(
            agreement=answers.review_state(self.review)['agreement'],
            requested_by_adviser=self.other,
            employer=self.match.offer.employer,
            decision='accepted',
            replies={'contact': 'no', 'conditions': [], 'interest': 'yes'},
            decided_at=timezone.now(),
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(
                reverse('shared_conversation_start', args=[self.review.pk])
            ).status_code,
            200,
        )
        self.client.force_login(self.adviser)
        self.assertEqual(
            self.client.get(
                reverse('shared_conversation_start', args=[self.review.pk])
            ).status_code,
            404,
        )

    def test_public_explanation_and_supplement_never_expose_internal_notes(self):
        self.finish()
        self.handle('claim')
        self.handle(
            'clarify',
            public_message='How much notice do you need?',
            internal_note='PRIVATE_ADVISER_NOTE',
        )
        self.client.force_login(self.candidate)
        page = self.client.get(
            reverse('candidate_offer_confirmation', args=[self.review.pk]) + '?lang=en'
        )
        self.assertContains(page, 'How much notice do you need?')
        self.assertNotContains(page, 'PRIVATE_ADVISER_NOTE')
        self.review.refresh_from_db()
        response = self.client.post(
            reverse('candidate_review_reply', args=[self.review.pk]),
            {
                'action': 'supplement',
                'version': self.review.workflow_version,
                'message': 'Three days.',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.review.refresh_from_db()
        self.assertEqual(self.review.summary['supplements'], ['Three days.'])
        self.assertEqual(self.review.workflow_state, 'claimed')
        self.handle(
            'refused',
            public_message='The employer requires earlier availability.',
            internal_note='ANOTHER_PRIVATE_NOTE',
        )
        page = self.client.get(
            reverse('candidate_offer_confirmation', args=[self.review.pk]) + '?lang=en'
        )
        self.assertContains(page, 'The employer requires earlier availability.')
        self.assertContains(
            page, 'Your profile remains available for other opportunities.'
        )
        self.assertNotContains(page, 'ANOTHER_PRIVATE_NOTE')

    def test_changed_answers_invalidate_decisions_and_keep_history(self):
        self.finish()
        self.handle('claim')
        event = self.handle('validated', public_message='Proceed')
        snapshot = self.review.events.get(action='submitted').snapshot
        row = next(
            r
            for r in answers.review_state(self.review)['rows']
            if r['kind'] == 'schedule'
        )
        answers.answer(
            self.candidate,
            self.review.pk,
            row['key'],
            row['fingerprint'],
            'conditional',
            'Three days notice',
            previous=row['answer'].pk,
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'waiting')
        self.assertFalse(workflow.current(self.review))
        self.assertEqual(self.review.events.get(action='submitted').snapshot, snapshot)
        with self.assertRaises(services.StaleEvaluation):
            self.handle('claim')
        state = answers.review_state(self.review)
        answers.agree(
            self.candidate,
            self.review.pk,
            state['fingerprint'],
            True,
            previous=self.review.profile_sharings.latest('pk').pk,
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'ready')
        self.assertEqual(self.review.events.filter(action='submitted').count(), 2)
        self.assertTrue(self.review.events.filter(pk=event.pk).exists())

    def test_context_change_blocks_stale_adviser_action(self):
        self.finish()
        self.handle('claim')
        self.match.offer.data['title'] = 'Changed offer'
        self.match.offer.save()
        with self.assertRaises(services.StaleEvaluation):
            self.handle('validated', public_message='Proceed')

    def test_adviser_alert_and_public_decision_email_use_only_safe_content(self):
        settings = dict(
            EMAIL_DELIVERY_ENABLED=True,
            DEMO_ACCOUNTS_ENABLED=False,
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            EMAIL_HOST='smtp.example.invalid',
            DEFAULT_FROM_EMAIL='no-reply@example.org',
            LOGIN_EMAIL_ORIGIN='https://testserver',
        )
        with self.settings(**settings), self.captureOnCommitCallbacks(execute=True):
            self.finish()
        self.assertEqual(mail.outbox[-1].to, [self.adviser.email])
        from tests.emails.assertions import assert_clickable_email

        assert_clickable_email(self, mail.outbox[-1])
        self.handle('claim')
        with self.settings(**settings), self.captureOnCommitCallbacks(execute=True):
            self.handle(
                'refused',
                public_message='The role starts too early.',
                internal_note='SECRET_INTERNAL_REASON',
            )
        self.assertEqual(mail.outbox[-1].to, [self.candidate.email])
        assert_clickable_email(self, mail.outbox[-1])
        self.assertIn('The role starts too early.', mail.outbox[-1].body)
        self.assertNotIn('SECRET_INTERNAL_REASON', str(mail.outbox))

    def test_role_ownership_csrf_and_legacy_completion(self):
        self.finish()
        stranger = Client()
        stranger.force_login(
            User.objects.create_user('stranger@example.org', kind='candidate')
        )
        reply = reverse('candidate_review_reply', args=[self.review.pk])
        self.assertEqual(stranger.post(reply, {'action': 'submit'}).status_code, 404)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.candidate)
        self.assertEqual(browser.post(reply, {'action': 'submit'}).status_code, 403)
        with self.assertRaises(PermissionDenied):
            self.handle('claim', self.candidate)
        CandidateOfferReview.objects.filter(pk=self.review.pk).update(
            workflow_state='waiting', submitted_fingerprint=''
        )
        self.client.force_login(self.candidate)
        self.assertEqual(
            self.client.post(
                reply,
                {
                    'action': 'submit',
                    'version': self.review.workflow_version,
                    'fingerprint': answers.review_state(self.review)['fingerprint'],
                },
            ).status_code,
            302,
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'ready')

    def refuse_schedule(self, match=None):
        match = match or self.match
        review = answers.request_offer_review(self.adviser, match.pk)
        row = next(
            r for r in answers.review_state(review)['rows'] if r['kind'] == 'schedule'
        )
        previous = row['answer'].pk if row['answer'] else 0
        answers.answer(
            self.candidate,
            review.pk,
            row['key'],
            row['fingerprint'],
            'no',
            previous=previous,
        )
        return review, row

    def another_match(self):
        offer = copy(self.match.offer)
        offer.pk = None
        offer._state = copy(offer._state)
        offer._state.adding = True
        offer.save()
        return CandidateOfferMatch.objects.create(
            candidate=self.match.candidate, offer=offer
        )

    def test_third_refusal_counts_distinct_offers_and_never_updates_profile(self):
        before = self.match.candidate.updated_at
        self.refuse_schedule()
        self.refuse_schedule()
        self.assertFalse(CandidateProfileReviewSuggestion.objects.exists())
        self.refuse_schedule(self.another_match())
        self.assertFalse(CandidateProfileReviewSuggestion.objects.exists())
        self.refuse_schedule(self.another_match())
        prompt = CandidateProfileReviewSuggestion.objects.get()
        self.assertEqual(len({e['offer'] for e in prompt.evidence}), 3)
        self.match.candidate.refresh_from_db()
        self.assertEqual(self.match.candidate.updated_at, before)
        self.client.force_login(self.candidate)
        self.assertContains(
            self.client.get(
                reverse('candidate_offer_confirmation', args=[self.review.pk])
                + '?lang=en'
            ),
            'three different offers',
        )
        workflow.resolve_prompt(self.candidate, prompt.pk, 'keep')
        self.assertFalse(workflow.prompts(self.review).exists())
        self.assertEqual(self.match.candidate.updated_at, before)

    def test_corrected_refusal_and_different_condition_do_not_count(self):
        review, row = self.refuse_schedule()
        answer = review.answers.get(question_key=row['key'])
        answers.answer(
            self.candidate,
            review.pk,
            row['key'],
            row['fingerprint'],
            'yes',
            previous=answer.pk,
        )
        self.refuse_schedule(self.another_match())
        self.refuse_schedule(self.another_match())
        self.assertFalse(CandidateProfileReviewSuggestion.objects.exists())

    def test_closure_and_all_decisions_render_in_three_languages(self):
        self.finish()
        self.handle('claim')
        self.handle('clarify', public_message='Please clarify the start date.')
        for language in ('fr', 'en', 'de'):
            self.client.force_login(self.adviser)
            self.assertContains(
                self.client.get(self.url, {'lang': language}), 'id="handling-title"'
            )
            self.client.force_login(self.candidate)
            page = self.client.get(
                reverse('candidate_offer_confirmation', args=[self.review.pk]),
                {'lang': language},
            )
            self.assertContains(page, 'id="handoff-title"')
            self.assertContains(page, 'id="review-supplement"')

    def test_profile_review_choice_opens_a_draft_without_writing_the_profile(self):
        for match in (self.match, self.another_match(), self.another_match()):
            self.refuse_schedule(match)
        prompt = CandidateProfileReviewSuggestion.objects.get()
        before = self.match.candidate.updated_at
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse('candidate_review_reply', args=[self.review.pk]),
            {'action': 'review', 'prompt': prompt.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('candidate_prepare'), response.url)
        self.match.candidate.refresh_from_db()
        self.assertEqual(self.match.candidate.updated_at, before)
        prompt.refresh_from_db()
        self.assertEqual(prompt.resolution, 'review')

    def test_prompt_becomes_unavailable_after_a_refusal_is_corrected(self):
        for match in (self.match, self.another_match(), self.another_match()):
            self.refuse_schedule(match)
        prompt = CandidateProfileReviewSuggestion.objects.get()
        row = next(
            r
            for r in answers.review_state(self.review)['rows']
            if r['kind'] == 'schedule'
        )
        answers.answer(
            self.candidate,
            self.review.pk,
            row['key'],
            row['fingerprint'],
            'yes',
            previous=row['answer'].pk,
        )
        self.assertFalse(workflow.prompts(self.review).exists())
        with self.assertRaises(services.StaleEvaluation):
            workflow.resolve_prompt(self.candidate, prompt.pk, 'review')

    def test_unrelated_profile_change_does_not_erase_current_refusals(self):
        self.refuse_schedule()
        self.refuse_schedule(self.another_match())
        profile = self.match.candidate
        profile.display_name = 'Different fictional display name'
        profile.save()
        self.refuse_schedule(self.another_match())
        self.assertEqual(CandidateProfileReviewSuggestion.objects.count(), 1)

    def test_different_requirement_never_counts_as_the_same_condition(self):
        self.refuse_schedule()
        self.refuse_schedule(self.another_match())
        match = self.another_match()
        match.offer.structured_requirements['schedule'] = ['sunday:morning']
        match.offer.save()
        self.refuse_schedule(match)
        self.assertFalse(CandidateProfileReviewSuggestion.objects.exists())

    def test_released_clarification_can_be_claimed_without_losing_the_question(self):
        self.finish()
        self.handle('claim')
        self.handle('clarify', public_message='What notice do you need?')
        self.handle('release')
        self.handle('claim', self.other)
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'clarify')
        workflow.supplement(
            self.candidate, self.review.pk, self.review.workflow_version, 'Three days'
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'claimed')
        self.assertEqual(self.review.assigned_to_adviser, self.other)

    def test_ordinary_advisers_have_the_same_workflow_in_all_environments(self):
        self.finish()
        for environment in ('local', 'preview', 'production'):
            with self.settings(
                DEMO_ACCOUNTS_ENABLED=False, DJANGO_ENVIRONMENT=environment
            ):
                self.handle('claim', self.other)
                self.handle('release', self.other)

    def test_delivery_failure_keeps_the_decision_and_safe_in_app_explanation(self):
        self.finish()
        self.handle('claim')
        with (
            self.settings(
                EMAIL_DELIVERY_ENABLED=True,
                DEMO_ACCOUNTS_ENABLED=False,
                EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                EMAIL_HOST='smtp.example.invalid',
                DEFAULT_FROM_EMAIL='no-reply@example.org',
                LOGIN_EMAIL_ORIGIN='https://testserver',
            ),
            patch(
                'eures_beta.matching.review_notifications.send_mail',
                side_effect=OSError('private failure'),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.handle(
                'refused',
                public_message='The role starts too early.',
                internal_note='Private',
            )
        self.review.refresh_from_db()
        self.assertEqual(self.review.workflow_state, 'refused')
        self.assertEqual(
            self.review.events.get(action='refused').delivery_status, 'failed'
        )

    def test_quick_refusal_of_a_profile_match_requires_explicit_scope(self):
        self.client.force_login(self.candidate)
        dialogue = reverse('candidate_offer_dialogue', args=[self.review.pk])
        row = next(
            r
            for r in answers.review_state(self.review)['rows']
            if r['kind'] == 'schedule'
        )
        before = self.match.candidate.updated_at
        self.client.post(
            dialogue,
            {
                'action': 'quick',
                'key': row['key'],
                'fingerprint': row['fingerprint'],
                'previous': 0,
                'value': 'no',
            },
        )
        state = answers.review_state(self.review)
        self.assertEqual(state['scope_pending']['key'], row['key'])
        for language in ('fr', 'en', 'de'):
            page = self.client.get(dialogue, {'lang': language})
            self.assertContains(page, 'id="scope-title"')
        previous = self.review.answers.latest('pk').pk
        result = self.client.post(
            reverse('candidate_review_reply', args=[self.review.pk]),
            {
                'action': 'scope',
                'key': row['key'],
                'fingerprint': row['fingerprint'],
                'previous': previous,
                'scope': 'offer',
            },
        )
        self.assertEqual(result.status_code, 302)
        self.assertIsNone(answers.review_state(self.review)['scope_pending'])
        self.assertEqual(self.review.answers.latest('pk').dialogue['scope'], 'offer')
        self.assertEqual(self.review.answers.count(), 2)
        self.match.candidate.refresh_from_db()
        self.assertEqual(self.match.candidate.updated_at, before)
        self.assertEqual(
            self.client.post(
                reverse('candidate_review_reply', args=[self.review.pk]),
                {
                    'action': 'scope',
                    'key': row['key'],
                    'fingerprint': row['fingerprint'],
                    'previous': previous,
                    'scope': 'profile',
                },
            ).status_code,
            409,
        )

    def test_general_scope_opens_review_without_changing_the_profile(self):
        self.client.force_login(self.candidate)
        row = next(
            r
            for r in answers.review_state(self.review)['rows']
            if r['kind'] == 'schedule'
        )
        before = self.match.candidate.updated_at
        event = answers.answer(
            self.candidate,
            self.review.pk,
            row['key'],
            row['fingerprint'],
            'no',
            dialogue={'scope': ''},
        )
        response = self.client.post(
            reverse('candidate_review_reply', args=[self.review.pk]),
            {
                'action': 'scope',
                'key': row['key'],
                'fingerprint': row['fingerprint'],
                'previous': event.pk,
                'scope': 'profile',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('candidate_prepare'), response.url)
        self.assertEqual(self.review.answers.latest('pk').dialogue['scope'], 'profile')
        self.match.candidate.refresh_from_db()
        self.assertEqual(self.match.candidate.updated_at, before)
