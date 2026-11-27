"""Employer consent is additive and reversible on populated PostgreSQL data."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from eures_beta.matching.models import CandidateOfferReview, CandidateProfileSharing
from eures_beta.matching import offer_review_services
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class EmployerConsentMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        self.migrate('0026_rename_employer_candidate_review')
        super().tearDown()

    def test_review_rename_preserves_rows_table_and_sequence(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        review = offer_review_services.request_offer_review(adviser, match.pk)
        agreement = CandidateProfileSharing.objects.create(
            review=review, fingerprint='rename-proof', agreed=True
        )
        apps = self.migrate('0025_employer_consent_database_names')
        old = apps.get_model('matching', 'EmployerOfferConsent').objects.create(
            agreement_id=agreement.pk,
            adviser_id=adviser.pk,
            employer_id=match.offer.employer_id,
            questions=[{'condition': 'German'}],
            replies={'conditions': ['accepted']},
            decision='accepted',
        )

        def identifiers(table):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT %s::regclass::oid, pg_get_serial_sequence(%s, 'id')::regclass::oid",
                    [table, table],
                )
                return cursor.fetchone()

        before = identifiers('matching_employerofferconsent')
        apps = self.migrate('0026_rename_employer_candidate_review')
        renamed = apps.get_model('matching', 'EmployerCandidateReview').objects.get(
            pk=old.pk
        )
        self.assertEqual(renamed.agreement_id, agreement.pk)
        self.assertEqual(renamed.adviser_id, adviser.pk)
        self.assertEqual(renamed.replies, old.replies)
        self.assertEqual(renamed.questions, old.questions)
        self.assertEqual(renamed.decision, old.decision)
        self.assertEqual(identifiers('matching_employercandidatereview'), before)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass',
                ['matching_employercandidatereview'],
            )
            self.assertTrue(
                all(
                    name.startswith('matching_employercandidatereview_')
                    for name, in cursor.fetchall()
                )
            )
            names = connection.introspection.get_constraints(
                cursor, 'matching_employercandidatereview'
            )
            self.assertTrue(
                all(
                    name.startswith('matching_employercandidatereview_')
                    for name in names
                )
            )
        self.assertNotIn(
            'matching_employerofferconsent', connection.introspection.table_names()
        )
        apps = self.migrate('0025_employer_consent_database_names')
        self.assertEqual(identifiers('matching_employerofferconsent'), before)
        restored = apps.get_model('matching', 'EmployerOfferConsent').objects.get(
            pk=old.pk
        )
        self.assertEqual(restored.agreement_id, agreement.pk)
        self.assertEqual(restored.replies, old.replies)

    def test_forward_and_back_preserve_existing_review_and_candidate_agreement(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        match.decision = 'retained'
        match.save()
        review = offer_review_services.request_offer_review(adviser, match.pk)
        agreement = CandidateProfileSharing.objects.create(
            review=review, fingerprint='historical', agreed=True
        )
        self.migrate('0023_explicit_user_relations')
        apps = self.migrate('0024_employer_offer_consent')
        consent = apps.get_model('matching', 'EmployerOfferConsent').objects.create(
            agreement_id=agreement.pk,
            adviser_id=adviser.pk,
            employer_id=match.offer.employer_id,
            questions=[{'condition': 'German', 'expected': 'B2'}],
        )
        self.migrate('0025_employer_consent_database_names')
        with connection.cursor() as cursor:
            names = connection.introspection.get_constraints(
                cursor, 'matching_employerofferconsent'
            )
        self.assertTrue(
            all(name.startswith('matching_employerofferconsent_') for name in names)
        )
        self.migrate('0024_employer_offer_consent')
        self.assertTrue(
            apps.get_model('matching', 'EmployerOfferConsent')
            .objects.filter(pk=consent.pk)
            .exists()
        )
        self.assertEqual(consent.agreement_id, agreement.pk)
        self.assertTrue(CandidateOfferReview.objects.filter(pk=review.pk).exists())
        self.migrate('0023_explicit_user_relations')
        self.assertTrue(CandidateProfileSharing.objects.get(pk=agreement.pk).agreed)
        self.assertTrue(CandidateOfferReview.objects.filter(pk=review.pk).exists())
        self.assertNotIn(
            'matching_employerofferconsent', connection.introspection.table_names()
        )
        self.migrate('0024_employer_offer_consent')
