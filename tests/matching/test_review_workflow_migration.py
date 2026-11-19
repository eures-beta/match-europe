from io import StringIO
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from eures_beta.matching.models import CandidateOfferReview


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class ReviewWorkflowMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_nonempty_upgrade_and_rollback_preserve_reviews_answers_and_consent(self):
        call_command('seed_test_accounts', stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        review = CandidateOfferReview.objects.first()
        from eures_beta.matching import offer_review_services as service

        row = next(r for r in service.review_state(review)['rows'] if r['askable'])
        answer = service.answer(
            review.match.candidate.user,
            review.pk,
            row['key'],
            row['fingerprint'],
            'yes',
        )
        # Preserve an existing recorded choice without suggesting it is currently valid.
        from eures_beta.matching.models import CandidateProfileSharing

        agreement = CandidateProfileSharing.objects.create(
            review=review,
            actor=review.match.candidate.user,
            fingerprint='0' * 64,
            agreed=False,
        )
        ids = (review.pk, answer.pk, agreement.pk)
        before = '0017_offer_review_email'
        after = '0019_review_database_names'
        old = self.migrate(before)
        self.assertTrue(
            old.get_model('matching', 'CandidateOfferReview')
            .objects.filter(pk=ids[0])
            .exists()
        )
        new = self.migrate(after)
        updated = new.get_model('matching', 'CandidateOfferReview').objects.get(
            pk=ids[0]
        )
        self.assertEqual(updated.workflow_state, 'waiting')
        self.assertEqual(updated.summary, {})
        self.assertFalse(
            new.get_model('matching', 'CandidateOfferReviewAction').objects.exists()
        )
        self.assertTrue(
            new.get_model('matching', 'CandidateOfferReviewAnswer')
            .objects.filter(pk=ids[1], review_id=ids[0])
            .exists()
        )
        self.assertFalse(
            new.get_model('matching', 'CandidateProfileSharing')
            .objects.get(pk=ids[2])
            .agreed
        )
        old = self.migrate(before)
        self.assertEqual(
            old.get_model('matching', 'CandidateOfferReviewAnswer')
            .objects.get(pk=ids[1])
            .value,
            'yes',
        )
        self.assertFalse(
            old.get_model('matching', 'CandidateProfileSharing')
            .objects.get(pk=ids[2])
            .agreed
        )
        self.migrate(after)
