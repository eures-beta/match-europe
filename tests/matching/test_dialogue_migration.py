"""Fresh and already deployed dialogue schemas survive the model renames."""

from io import StringIO

from django.core.management import call_command
from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase, override_settings

BEFORE = '0006_candidate_offer_model_names'
AFTER = '0007_candidate_offer_review_answer_dialogue'
LEGACY = '0006_confirmationanswer_dialogue'
TABLE = 'matching_confirmationanswer'


@override_settings(
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class DialogueMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def tearDown(self):
        # Remove the simulated historical recorder entry before normal restoration.
        MigrationRecorder(connection).record_unapplied('matching', LEGACY)
        apps = self.migrate(BEFORE)
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, TABLE)
        if any(column.name == 'dialogue' for column in columns):
            self.remove_column(apps)
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def field(self):
        field = models.JSONField(blank=True, default=dict)
        field.set_attributes_from_name('dialogue')
        return field

    def remove_column(self, apps):
        with connection.schema_editor() as editor:
            editor.remove_field(
                apps.get_model('matching', 'CandidateOfferReviewAnswer'), self.field()
            )

    def prepare(self):
        apps = self.migrate(BEFORE)
        call_command('seed_matching_trial', stdout=StringIO())
        pair = apps.get_model('matching', 'CandidateOfferMatch').objects.first()
        user = apps.get_model('users', 'User').objects.create(
            email='dialogue-migration@example.invalid', kind='adviser'
        )
        review = apps.get_model('matching', 'CandidateOfferReview').objects.create(
            pair_id=pair.pk, requested_by_id=user.pk
        )
        answer = apps.get_model(
            'matching', 'CandidateOfferReviewAnswer'
        ).objects.create(
            request_id=review.pk,
            actor_id=pair.candidate.user_id,
            question_key='schedule',
            fingerprint='a' * 64,
            presented={'expected': 'Saturday'},
            value='conditional',
            detail='Alternate weeks',
        )
        return apps, answer.pk

    def test_fresh_upgrade_and_rollback_preserve_answers(self):
        _, pk = self.prepare()
        apps = self.migrate(AFTER)
        answer = apps.get_model('matching', 'CandidateOfferReviewAnswer').objects.get(
            pk=pk
        )
        self.assertEqual(answer.dialogue, {})
        self.assertEqual(answer.detail, 'Alternate weeks')
        self.migrate(BEFORE)
        apps = self.migrate(AFTER)
        self.assertEqual(
            apps.get_model('matching', 'CandidateOfferReviewAnswer')
            .objects.get(pk=pk)
            .detail,
            'Alternate weeks',
        )

    def test_legacy_dialogue_is_adopted_without_rewriting_it(self):
        apps, pk = self.prepare()
        with connection.schema_editor() as editor:
            editor.add_field(
                apps.get_model('matching', 'CandidateOfferReviewAnswer'), self.field()
            )
        MigrationRecorder(connection).record_applied('matching', LEGACY)
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE matching_confirmationanswer SET dialogue=%s::jsonb WHERE id=%s',
                ['{"prompt":"Saturday?","turns":["Every other week"]}', pk],
            )
        apps = self.migrate(AFTER)
        expected = {'prompt': 'Saturday?', 'turns': ['Every other week']}
        self.assertEqual(
            apps.get_model('matching', 'CandidateOfferReviewAnswer')
            .objects.get(pk=pk)
            .dialogue,
            expected,
        )
        self.migrate(BEFORE)
        apps = self.migrate(AFTER)
        self.assertEqual(
            apps.get_model('matching', 'CandidateOfferReviewAnswer')
            .objects.get(pk=pk)
            .dialogue,
            expected,
        )

    def test_unrecorded_existing_column_is_refused(self):
        apps, _ = self.prepare()
        with connection.schema_editor() as editor:
            editor.add_field(
                apps.get_model('matching', 'CandidateOfferReviewAnswer'), self.field()
            )
        with self.assertRaisesMessage(RuntimeError, 'Unexpected dialogue schema'):
            self.migrate(AFTER)

    def test_legacy_record_with_missing_column_is_refused(self):
        self.prepare()
        MigrationRecorder(connection).record_applied('matching', LEGACY)
        with self.assertRaisesMessage(RuntimeError, 'Unexpected dialogue schema'):
            self.migrate(AFTER)

    def test_wrong_legacy_column_type_is_refused(self):
        self.prepare()
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE matching_confirmationanswer ADD COLUMN dialogue text NOT NULL DEFAULT %s',
                ['unexpected'],
            )
        MigrationRecorder(connection).record_applied('matching', LEGACY)
        with self.assertRaisesMessage(RuntimeError, 'Unexpected dialogue schema'):
            self.migrate(AFTER)
