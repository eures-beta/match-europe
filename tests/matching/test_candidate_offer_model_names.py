"""Business model renames preserve stored reviews and Django metadata."""

from io import StringIO

from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from eures_beta.matching import models

RENAMES = (
    ('MatchPair', 'CandidateOfferMatch', 'matching_matchpair'),
    ('ConfirmationRequest', 'CandidateOfferReview', 'matching_confirmationrequest'),
    ('ConfirmationAnswer', 'CandidateOfferReviewAnswer', 'matching_confirmationanswer'),
    (
        'TransmissionAgreement',
        'CandidateProfileSharing',
        'matching_transmissionagreement',
    ),
)
BEFORE = '0005_offer_confirmations'
AFTER = '0006_candidate_offer_model_names'


class CandidateOfferModelNamesTests(TestCase):
    def test_only_new_names_are_registered_and_admin_urls_use_them(self):
        for old, new, table in RENAMES:
            with self.subTest(model=new):
                self.assertFalse(hasattr(models, old))
                model = getattr(models, new)
                self.assertEqual(model._meta.db_table, table)
                self.assertTrue(admin.site.is_registered(model))
                self.assertEqual(
                    reverse(f'admin:matching_{new.lower()}_changelist'),
                    f'/admin/matching/{new.lower()}/',
                )


@override_settings(
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    SHARED_DEMO=False,
)
class CandidateOfferModelRenameMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', name)])
        ContentType.objects.clear_cache()
        return executor.loader.project_state([('matching', name)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def snapshot(self):
        result = {}
        tables = [table for _, _, table in RENAMES]
        tables += ['matching_evaluation', 'matching_decision']
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute('SELECT %s::regclass::oid', [table])
                oid = cursor.fetchone()[0]
                cursor.execute(
                    f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                )
                result[table] = oid, cursor.fetchall()
        return result

    def prepare(self):
        apps = self.migrate(BEFORE)
        call_command('seed_matching_trial', stdout=StringIO())
        pair = apps.get_model('matching', 'MatchPair').objects.first()
        adviser = apps.get_model('users', 'User').objects.create(
            email='rename-adviser@example.invalid', kind='adviser'
        )
        review = apps.get_model('matching', 'ConfirmationRequest').objects.create(
            pair_id=pair.pk, requested_by_id=adviser.pk
        )
        answer = apps.get_model('matching', 'ConfirmationAnswer').objects.create(
            request_id=review.pk,
            actor_id=pair.candidate.user_id,
            question_key='schedule:saturday:morning',
            fingerprint='a' * 64,
            presented={'expected': 'Fictional Saturday morning'},
            value='conditional',
            detail='Alternate Saturdays',
        )
        for agreed in (True, False):
            apps.get_model('matching', 'TransmissionAgreement').objects.create(
                request_id=review.pk,
                actor_id=pair.candidate.user_id,
                fingerprint='b' * 64,
                agreed=agreed,
            )
        evaluation = pair.evaluations.first()
        apps.get_model('matching', 'MatchDecision').objects.create(
            pair_id=pair.pk, evaluation_id=evaluation.pk, value='retained'
        )
        group = Group.objects.create(name='fictional-rename-metadata')
        metadata = []
        for old, new, _ in RENAMES:
            content_type, _ = ContentType.objects.get_or_create(
                app_label='matching', model=old.lower()
            )
            permissions = []
            for action in ('add', 'change', 'delete', 'view'):
                permission, _ = Permission.objects.get_or_create(
                    content_type=content_type,
                    codename=f'{action}_{old.lower()}',
                    defaults={'name': f'Can {action} fictional model'},
                )
                group.permissions.add(permission)
                permissions.append((permission.pk, action))
            metadata.append((content_type.pk, old.lower(), new.lower(), permissions))
        return pair.pk, review.pk, answer.pk, group, metadata

    def assert_metadata(self, metadata, group, *, renamed):
        for content_type_id, old, new, permissions in metadata:
            name = new if renamed else old
            content_type = ContentType.objects.get(pk=content_type_id)
            self.assertEqual(content_type.model, name)
            self.assertFalse(
                ContentType.objects.filter(
                    app_label='matching', model=old if renamed else new
                ).exists()
            )
            for permission_id, action in permissions:
                permission = Permission.objects.get(pk=permission_id)
                self.assertEqual(permission.content_type_id, content_type_id)
                self.assertEqual(permission.codename, f'{action}_{name}')
                self.assertTrue(group.permissions.filter(pk=permission_id).exists())

    def test_rename_and_rollback_preserve_rows_tables_relations_and_metadata(self):
        pair_id, review_id, answer_id, group, metadata = self.prepare()
        before = self.snapshot()
        with CaptureQueriesContext(connection) as queries:
            apps = self.migrate(AFTER)
        self.assertFalse(
            any(
                query['sql'].lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP '))
                for query in queries
            )
        )
        self.assertEqual(self.snapshot(), before)
        self.assert_metadata(metadata, group, renamed=True)
        pair = apps.get_model('matching', 'CandidateOfferMatch').objects.get(pk=pair_id)
        self.assertEqual(pair.candidate_offer_review.pk, review_id)
        review = pair.candidate_offer_review
        self.assertEqual(review.answers.get().pk, answer_id)
        self.assertEqual(review.answers.get().detail, 'Alternate Saturdays')
        self.assertEqual(
            list(review.agreements.order_by('pk').values_list('agreed', flat=True)),
            [True, False],
        )
        self.assertEqual(pair.evaluations.count(), 1)
        self.assertEqual(pair.decisions.get().value, 'retained')
        self.migrate(BEFORE)
        self.assertEqual(self.snapshot(), before)
        self.assert_metadata(metadata, group, renamed=False)
        apps = self.migrate(AFTER)
        self.assertEqual(self.snapshot(), before)
        self.assert_metadata(metadata, group, renamed=True)
        answer = apps.get_model(
            'matching', 'CandidateOfferReviewAnswer'
        ).objects.create(
            request_id=review_id,
            actor_id=review.answers.get().actor_id,
            question_key='working_time:',
            fingerprint='c' * 64,
            presented={'expected': 'Fictional working hours'},
            value='yes',
        )
        self.assertGreater(answer.pk, answer_id)

    def test_conflicting_metadata_is_refused_without_losing_business_rows(self):
        self.prepare()
        before = self.snapshot()
        conflict = ContentType.objects.create(
            app_label='matching', model='candidateofferreview'
        )
        try:
            with self.assertRaisesMessage(
                RuntimeError, 'Conflicting matching content types'
            ):
                self.migrate(AFTER)
            self.assertEqual(self.snapshot(), before)
            self.assertTrue(
                ContentType.objects.filter(
                    app_label='matching', model='matchpair'
                ).exists()
            )
        finally:
            conflict.delete()
