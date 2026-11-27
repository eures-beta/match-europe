from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier

from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, override_settings

from eures_beta.introductions import (
    offer_review_services as answers,
    review_workflow as workflow,
)
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.matching.services import StaleEvaluation
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class ReviewConcurrencyTests(TransactionTestCase):
    def setUp(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        self.adviser = prepared_user('adviser')
        self.other = User.objects.create_user(
            'other-handler@example.org', kind='adviser'
        )
        match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        match.decision = 'retained'
        match.save()
        self.review = answers.request_offer_review(self.adviser, match.pk)
        for row in answers.review_state(self.review)['rows']:
            if row['askable']:
                answers.answer(
                    match.candidate.user,
                    self.review.pk,
                    row['key'],
                    row['fingerprint'],
                    'yes',
                )
        state = answers.review_state(self.review)
        answers.agree(match.candidate.user, self.review.pk, state['fingerprint'], True)
        self.review.refresh_from_db()
        self.fingerprint = state['fingerprint']

    def race(self, actions):
        barrier = Barrier(2)
        version = self.review.workflow_version

        def run(args):
            close_old_connections()
            user_id, action, message = args
            try:
                user = User.objects.get(pk=user_id)
                barrier.wait(timeout=10)
                workflow.handle(
                    user,
                    self.review.pk,
                    action,
                    version,
                    self.fingerprint,
                    public_message=message,
                )
                return 'saved'
            except StaleEvaluation:
                return 'stale'
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, actions))

    def test_two_advisers_cannot_both_claim_the_review(self):
        result = self.race(
            [(self.adviser.pk, 'claim', ''), (self.other.pk, 'claim', '')]
        )
        self.assertCountEqual(result, ['saved', 'stale'])
        self.assertEqual(self.review.events.filter(action='claim').count(), 1)

    def test_two_tabs_cannot_record_conflicting_decisions(self):
        workflow.handle(
            self.adviser,
            self.review.pk,
            'claim',
            self.review.workflow_version,
            self.fingerprint,
        )
        self.review.refresh_from_db()
        result = self.race(
            [
                (self.adviser.pk, 'validated', 'We can proceed.'),
                (self.adviser.pk, 'refused', 'Conditions do not fit.'),
            ]
        )
        self.assertCountEqual(result, ['saved', 'stale'])
        self.assertEqual(
            self.review.events.filter(action__in=['validated', 'refused']).count(), 1
        )
