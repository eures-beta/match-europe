from io import StringIO
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from eures_beta.matching.models import CandidateOfferReview
from django.contrib.contenttypes.models import ContentType


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
        ContentType.objects.clear_cache()
        super().tearDown()

    def test_nonempty_upgrade_and_rollback_preserve_reviews_answers_and_consent(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
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

    def test_event_rename_roundtrip_preserves_history_database_objects_and_permissions(
        self,
    ):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        review = CandidateOfferReview.objects.first()
        old = self.migrate('0019_review_database_names')
        Event = old.get_model('matching', 'CandidateOfferReviewAction')
        event = Event.objects.create(
            id=101,
            review_id=review.pk,
            actor_id=review.requested_by_adviser_id,
            version=7,
            action='submitted',
            internal_note='Fictional internal note',
            public_message='Fictional explanation',
            snapshot={'preserve': ['summary']},
            delivery_status='sent',
        )
        expected = Event.objects.filter(pk=event.pk).values().get()
        content_type, _ = old.get_model(
            'contenttypes', 'ContentType'
        ).objects.get_or_create(
            app_label='matching', model='candidateofferreviewaction'
        )
        permission, _ = old.get_model('auth', 'Permission').objects.get_or_create(
            content_type=content_type,
            codename='view_candidateofferreviewaction',
            defaults={'name': 'Can view candidate offer review action'},
        )
        group = old.get_model('auth', 'Group').objects.create(
            name='Fictional journal observers'
        )
        group.permissions.add(permission)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT setval(pg_get_serial_sequence(%s, %s), 333, true)',
                [Event._meta.db_table, 'id'],
            )

        def identity(model):
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT %s::regclass::oid, pg_get_serial_sequence(%s, %s)::regclass::oid',
                    [model._meta.db_table, model._meta.db_table, 'id'],
                )
                table_oid, sequence_oid = cursor.fetchone()
                cursor.execute(
                    'SELECT last_value FROM pg_sequences WHERE schemaname=current_schema() AND sequencename=(SELECT relname FROM pg_class WHERE oid=%s)',
                    [sequence_oid],
                )
                return table_oid, sequence_oid, cursor.fetchone()[0]

        physical = identity(Event)
        for migration, name in (
            ('0020_candidate_offer_review_event', 'CandidateOfferReviewEvent'),
            ('0019_review_database_names', 'CandidateOfferReviewAction'),
            ('0020_candidate_offer_review_event', 'CandidateOfferReviewEvent'),
        ):
            state = self.migrate(migration)
            Event = state.get_model('matching', name)
            self.assertEqual(identity(Event), physical)
            self.assertEqual(Event.objects.filter(pk=event.pk).values().get(), expected)
            self.assertEqual(Event.objects.get(pk=event.pk).review_id, review.pk)
            self.assertTrue(
                group.permissions.filter(
                    pk=permission.pk, content_type_id=content_type.pk
                ).exists()
            )
            self.assertEqual(
                state.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .model,
                name.lower(),
            )
            self.assertEqual(
                state.get_model('auth', 'Permission')
                .objects.get(pk=permission.pk)
                .codename,
                'view_' + name.lower(),
            )
        next_event = Event.objects.create(
            review_id=review.pk,
            actor_id=review.requested_by_adviser_id,
            version=8,
            action='claim',
        )
        self.assertGreater(next_event.pk, 333)
