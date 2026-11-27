"""Three overlapping source identifiers and all payloads survive a round trip."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)
class MatchEventMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        targets = [('matching', name)]
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_rollback_refuses_to_discard_history_after_its_review_was_removed(self):
        from eures_beta.introductions.models import CandidateOfferReview
        from eures_beta.matching.models import MatchEvent

        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.first()
        review, _ = CandidateOfferReview.objects.get_or_create(
            match=match, defaults={'requested_by_adviser': adviser}
        )
        event = MatchEvent.objects.create(
            match=match,
            kind='review',
            actor=adviser,
            action='claim',
            version=1,
            internal_note='Keep this history even without its old review',
        )
        review.delete()
        with self.assertRaisesMessage(
            RuntimeError, 'original domain record was removed'
        ):
            self.migrate('0036_complete_domain_extraction')
        self.assertTrue(MatchEvent.objects.filter(pk=event.pk).exists())
        self.migrate('0038_complete_event_fusion')

    def test_populated_journals_round_trip_with_colliding_identifiers(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        call_command('seed_matching_trial', stdout=StringIO())
        adviser = prepared_user('adviser')
        match = CandidateOfferMatch.objects.first()
        apps = self.migrate('0036_complete_domain_extraction')
        review, _ = apps.get_model(
            'introductions', 'CandidateOfferReview'
        ).objects.get_or_create(
            match_id=match.pk, defaults={'requested_by_adviser_id': adviser.pk}
        )
        plan = apps.get_model('followup', 'MatchFollowup').objects.create(
            match_id=match.pk,
            updated_by_adviser_id=adviser.pk,
            waiting_for='candidate',
            next_action='Keep this plan',
        )
        conclusion = apps.get_model('followup', 'MatchConclusion').objects.create(
            match_id=match.pk,
            state='stopped',
            confirmed_by_adviser_id=adviser.pk,
            confirmed_at=timezone.now(),
            reason='Keep this reason',
            version=1,
        )
        records = (
            (
                'introductions',
                'CandidateOfferReviewEvent',
                dict(
                    review_id=review.pk,
                    version=1,
                    action='clarify',
                    internal_note='PRIVATE_NOTE',
                    public_message='Public clarification',
                    snapshot={'answers': ['original']},
                    delivery_status='failed',
                ),
            ),
            (
                'followup',
                'MatchFollowupEvent',
                dict(
                    followup_id=plan.pk,
                    action='reminder',
                    recipient='candidate',
                    message='Reminder text',
                    snapshot={'next_action': 'Original plan'},
                    delivery_status='disabled',
                ),
            ),
            (
                'followup',
                'MatchConclusionEvent',
                dict(
                    conclusion_id=conclusion.pk,
                    action='stopped',
                    version=1,
                    reason='Original conclusion reason',
                    start_on=timezone.localdate(),
                ),
            ),
        )
        stamp = timezone.now() - timezone.timedelta(days=5)
        for app, name, fields in records:
            model = apps.get_model(app, name)
            model.objects.create(pk=100000, actor_id=adviser.pk, **fields)
            model.objects.filter(pk=100000).update(created_at=stamp)
        apps = self.migrate('0038_complete_event_fusion')
        Event = apps.get_model('matching', 'MatchEvent')
        events = list(Event.objects.filter(source_id=100000).order_by('kind'))
        self.assertEqual({e.kind for e in events}, {'review', 'followup', 'conclusion'})
        self.assertEqual(len({e.pk for e in events}), 3)
        for event in events:
            self.assertEqual(
                (event.match_id, event.actor_id, event.created_at),
                (match.pk, adviser.pk, stamp),
            )
        self.assertEqual(
            Event.objects.get(kind='review', source_id=100000).internal_note,
            'PRIVATE_NOTE',
        )
        self.assertEqual(
            Event.objects.get(kind='followup', source_id=100000).delivery_status,
            'disabled',
        )
        self.assertEqual(
            Event.objects.get(kind='conclusion', source_id=100000).reason,
            'Original conclusion reason',
        )
        Event.objects.create(
            match_id=match.pk,
            kind='review',
            action='claim',
            actor_id=adviser.pk,
            version=2,
        )
        apps = self.migrate('0036_complete_domain_extraction')
        for app, name, fields in records:
            restored = apps.get_model(app, name).objects.get(pk=100000)
            self.assertEqual(restored.created_at, stamp)
            for field, value in fields.items():
                self.assertEqual(getattr(restored, field), value)
        self.assertTrue(
            apps.get_model('introductions', 'CandidateOfferReviewEvent')
            .objects.filter(review_id=review.pk, version=2)
            .exists()
        )
        self.migrate('0038_complete_event_fusion')
