from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.matching import offer_review_services as service
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.test_accounts import prepared_user
from eures_beta.www.adviser.matching import record_review


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
)
class CandidateInboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', stdout=StringIO())

    def setUp(self):
        self.user = prepared_user('candidate-pwa')
        self.match = CandidateOfferMatch.objects.get(candidate__user=self.user)
        record_review(
            prepared_user('adviser'),
            self.match,
            self.match.evaluations.latest('pk').pk,
            'retained',
        )
        self.review = self.match.candidate_offer_review
        self.client.force_login(self.user)
        self.url = reverse('candidate_offer_inbox')

    def entry(self):
        return self.client.get(self.url, {'lang': 'en'}).context['entries'][0]

    def answer(self, kind='occupation', value='yes'):
        row = next(
            row
            for row in service.review_state(self.review)['rows']
            if row['kind'] == kind
        )
        return service.answer(
            self.user, self.review.pk, row['key'], row['fingerprint'], value
        )

    def test_new_offer_is_visible_on_profile_even_if_email_failed(self):
        self.review.email_status = 'failed'
        self.review.save(update_fields=['email_status'])
        self.assertTrue(self.entry()['is_new'])
        self.assertEqual(self.entry()['progress'], 'not_started')
        page = self.client.get(reverse('candidate_profile'), {'lang': 'en'})
        self.assertEqual(page.context['new_offer_count'], 1)
        self.assertContains(page, 'A new offer to review')
        self.assertEqual(self.entry()['target'], 'candidate_offer_dialogue')
        self.assertFalse(self.review.answers.exists())

    def test_first_answer_removes_new_badge_and_allows_resume(self):
        self.answer()
        self.assertFalse(self.entry()['is_new'])
        self.assertEqual(self.entry()['progress'], 'in_progress')
        self.assertEqual(self.entry()['target'], 'candidate_offer_dialogue')

    def test_answers_alone_do_not_complete_the_journey(self):
        for row in service.review_state(self.review)['rows']:
            if row['askable']:
                service.answer(
                    self.user, self.review.pk, row['key'], row['fingerprint'], 'yes'
                )
        self.assertEqual(self.entry()['progress'], 'in_progress')
        self.assertEqual(self.entry()['target'], 'candidate_offer_confirmation')
        state = service.review_state(self.review)
        service.agree(self.user, self.review.pk, state['fingerprint'], False)
        self.assertEqual(self.entry()['progress'], 'completed')

    def test_changed_offer_reopens_completed_journey(self):
        self.test_answers_alone_do_not_complete_the_journey()
        self.match.offer.data['title'] = 'Changed fictional offer'
        self.match.offer.save()
        self.assertEqual(self.entry()['progress'], 'in_progress')
        self.assertFalse(self.entry()['is_new'])

    def test_declined_offer_has_an_explicit_status_and_no_new_badge(self):
        self.answer(value='no')
        self.assertEqual(self.entry()['progress'], 'declined')
        self.assertFalse(self.entry()['is_new'])
        self.assertFalse(self.review.profile_sharings.exists())

    def test_offer_cards_do_not_expose_another_candidates_reviews(self):
        other = prepared_user('candidate-pwa-replay')
        self.client.force_login(other)
        page = self.client.get(self.url)
        self.assertNotIn(
            self.review.pk, [entry['review'].pk for entry in page.context['entries']]
        )

    def test_guided_fallback_and_translated_cards(self):
        for language in ('fr', 'en', 'de'):
            with self.subTest(language=language):
                self.assertContains(
                    self.client.get(self.url, {'lang': language}),
                    self.match.offer.data['title'],
                )
        with self.settings(ALBERT_SIMULATED=False, ALBERT_API_KEY=''):
            self.assertEqual(self.entry()['target'], 'candidate_offer_confirmation')
