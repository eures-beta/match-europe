"""One journal preserves scoped histories, concurrency and adviser-only payloads."""

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.matching.models import MatchEvent
from eures_beta.followup.models import MatchFollowup, MatchConclusion
from tests.introductions import test_review_workflow as fixtures


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class MatchEventTests(TestCase):
    setUpTestData = classmethod(fixtures.ReviewWorkflowTests.setUpTestData.__func__)

    def setUp(self):
        fixtures.ReviewWorkflowTests.setUp(self)

    def event(self, kind='review', action='claim', version=1, **kwargs):
        return MatchEvent.objects.create(
            match=self.match,
            actor=self.adviser,
            kind=kind,
            action=action,
            version=version,
            **kwargs,
        )

    def test_one_match_keeps_independent_versions_and_scoped_histories(self):
        review = self.event(public_message='Public review message')
        followup = self.event(
            'followup',
            'plan',
            None,
            public_message='PRIVATE_FOLLOWUP',
            message='PRIVATE_REMINDER',
        )
        conclusion = self.event('conclusion', 'stopped', 1, reason='PRIVATE_REASON')
        plan = MatchFollowup.objects.create(
            match=self.match,
            updated_by_adviser=self.adviser,
            waiting_for='adviser',
            next_action='Follow up',
        )
        result = MatchConclusion.objects.create(
            match=self.match,
            state='stopped',
            reason='Stopped',
            confirmed_by_adviser=self.adviser,
            confirmed_at=conclusion.created_at,
        )
        self.assertEqual(
            set(self.match.events.values_list('pk', flat=True)),
            {review.pk, followup.pk, conclusion.pk},
        )
        self.assertEqual(
            list(self.review.events.values_list('pk', flat=True)), [review.pk]
        )
        self.assertEqual(list(plan.events.values_list('pk', flat=True)), [followup.pk])
        self.assertEqual(
            list(result.events.values_list('pk', flat=True)), [conclusion.pk]
        )
        self.assertEqual(
            list(
                self.review.events.exclude(public_message='').values_list(
                    'public_message', flat=True
                )
            ),
            ['Public review message'],
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.event()

    def test_database_rejects_wrong_kind_action_and_author_even_in_bulk(self):
        invalid = [
            dict(kind='review', action='plan', version=1, actor=self.adviser),
            dict(kind='followup', action='plan', version=1, actor=self.adviser),
            dict(kind='followup', action='reminder', actor=self.candidate),
            dict(kind='conclusion', action='reported', version=1, actor=self.adviser),
            dict(kind='conclusion', action='stopped', version=1, actor=self.candidate),
        ]
        for fields in invalid:
            with (
                self.subTest(fields=fields),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                MatchEvent.objects.bulk_create([MatchEvent(match=self.match, **fields)])

    def test_history_survives_removal_of_the_domain_record(self):
        event = self.event(internal_note='Preserved adviser-only audit')
        self.review.delete()
        event.refresh_from_db()
        self.assertEqual(event.match_id, self.match.pk)
        self.assertEqual(event.internal_note, 'Preserved adviser-only audit')

    def test_candidate_http_page_never_reads_another_event_category(self):
        self.event(
            action='clarify',
            public_message='Public clarification',
            internal_note='PRIVATE_ADVISER_NOTE',
        )
        self.event(
            'followup',
            'reminder',
            None,
            public_message='PRIVATE_FOLLOWUP',
            message='PRIVATE_REMINDER',
        )
        self.event(
            'conclusion',
            'stopped',
            1,
            public_message='PRIVATE_CONCLUSION',
            reason='PRIVATE_REASON',
        )
        self.client.force_login(self.candidate)
        page = self.client.get(
            reverse('candidate_offer_confirmation', args=[self.review.pk]), follow=True
        )
        self.assertContains(page, 'Public clarification')
        for private in (
            'PRIVATE_ADVISER_NOTE',
            'PRIVATE_FOLLOWUP',
            'PRIVATE_REMINDER',
            'PRIVATE_CONCLUSION',
            'PRIVATE_REASON',
        ):
            self.assertNotContains(page, private)
