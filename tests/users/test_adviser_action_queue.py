from datetime import timedelta
from io import StringIO
import re

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer
from eures_beta.matching import search_queue, services
from eures_beta.matching.models import (
    CandidateSupport,
    JobOfferSupport,
    CandidateOfferMatch,
    CandidateOfferReview,
)
from eures_beta.users.models import User
from eures_beta.users.test_accounts import prepared_user
from tests.matching.test_dialogue import SETTINGS


@override_settings(**{**SETTINGS, 'ALBERT_SIMULATED': True})
class AdviserActionQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', stdout=StringIO())
        cls.adviser = prepared_user('adviser')
        cls.candidate = CandidateProfile.objects.get(
            user__email='compatible@matching-trial.invalid'
        )
        cls.match = CandidateOfferMatch.objects.get(candidate=cls.candidate)
        cls.offer = cls.match.offer

    def setUp(self):
        CandidateProfile.objects.exclude(pk=self.candidate.pk).delete()
        JobOffer.objects.exclude(pk=self.offer.pk).delete()
        CandidateOfferReview.objects.all().delete()
        self.client.force_login(self.adviser)
        self.url = reverse('dashboard')
        self.offer_url = reverse('adviser_search', args=['offers', self.offer.pk])
        self.candidate_url = reverse(
            'adviser_search', args=['candidates', self.candidate.pk]
        )
        services.calculate(self.candidate, self.offer)

    def test_navigation_and_pending_match_are_preserved(self):
        response = self.client.get(self.url, {'lang': 'fr'})
        self.assertContains(response, 'Rapprochements à valider')
        self.assertContains(response, 'aria-label="1 action à traiter"')
        self.assertContains(response, 'class="adviser-action-count"', count=1)
        self.assertEqual(
            [item['count'] for item in response.context['queue_navigation']], [1, 0, 0]
        )
        self.assertContains(response, reverse('adviser_match', args=[self.match.pk]))
        self.assertContains(response, 'value="retained"')
        self.assertEqual(search_queue.search_rows(), {'offers': [], 'candidates': []})

    def test_adviser_pages_load_existing_stylesheets(self):
        self.candidate.delete()
        for url in (self.url, self.offer_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                stylesheets = re.findall(
                    r'<link[^>]+href="/static/([^"?]+\.css)"',
                    response.content.decode(),
                )
                self.assertTrue(stylesheets)
                for name in stylesheets:
                    self.assertIsNotNone(finders.find(name), name)

    def test_offer_with_no_candidate_is_an_external_search(self):
        self.candidate.delete()
        row = search_queue.search_rows()['offers'][0]
        self.assertEqual(row['reason'], 'no_candidates')
        response = self.client.get(self.url, {'view': 'offers'})
        self.assertContains(response, self.offer_url)
        self.assertEqual(response.context['queue_navigation'][1]['count'], 1)
        self.assertContains(self.client.get(self.offer_url), self.offer.data['title'])

    def test_candidate_with_no_offer_is_prospecting(self):
        self.offer.delete()
        row = search_queue.search_rows()['candidates'][0]
        self.assertEqual(row['reason'], 'no_offers')
        self.assertContains(
            self.client.get(self.candidate_url), self.candidate.display_name
        )

    def test_calculated_incompatibility_is_external_search(self):
        self.offer.data['requirements'] = {'permitRequired': 'yes', 'permits': ['C']}
        self.offer.structured_requirements = {'mandatory_permits': ['C']}
        self.offer.save()
        self.match.candidate_facts = {'licences_not_held_at_start': ['C']}
        self.match.save(update_fields=['candidate_facts'])
        evaluation = services.calculate(self.candidate, self.offer)
        self.assertEqual(evaluation.result['status'], 'blocked')
        self.assertEqual(search_queue.search_rows()['offers'][0]['reason'], 'none')
        self.assertEqual(search_queue.search_rows()['candidates'][0]['reason'], 'none')

    def test_insufficient_evidence_is_not_incompatibility(self):
        evaluation = self.match.evaluations.latest('pk')
        evaluation.result['status'] = 'insufficient'
        evaluation.save(update_fields=['result'])
        self.assertEqual(
            search_queue.search_rows()['offers'][0]['reason'], 'incomplete'
        )

    def test_offer_sheet_preserves_readable_content_and_escapes_input(self):
        self.candidate.delete()
        self.offer.data.update(
            description='First line\nSecond line <script>alert(1)</script>',
            desiredProfile='Experience required',
            contractType='PERMANENT_CONTRACT',
        )
        self.offer.save()
        response = self.client.get(self.offer_url, {'lang': 'fr'})
        self.assertContains(response, 'First line<br>Second line &lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, 'Experience required')
        self.assertContains(response, 'CDI')
        self.assertNotContains(response, 'PERMANENT_CONTRACT')
        self.assertNotContains(response, 'Non renseigné')

    def test_candidate_sheet_shows_project_country_and_language_labels(self):
        self.offer.delete()
        response = self.client.get(self.candidate_url, {'lang': 'fr'})
        self.assertContains(response, 'France')
        self.assertContains(response, 'Français — B1')
        self.assertContains(response, self.candidate.display_name)
        self.assertContains(response, 'Ouvert à différents métiers')
        self.assertContains(response, 'Enregistrer le suivi')

    def test_missing_calculation_is_not_a_negative_result(self):
        CandidateOfferMatch.objects.all().delete()
        for rows in search_queue.search_rows().values():
            self.assertEqual(rows[0]['reason'], 'pending')
            self.assertFalse(rows[0]['actionable'])

    def test_changed_input_invalidates_negative_results(self):
        self.match.decision = 'refused'
        self.match.save(update_fields=['decision'])
        self.candidate.desired_countries = ['DE']
        self.candidate.save()
        self.assertEqual(search_queue.search_rows()['offers'][0]['reason'], 'pending')

    def test_changed_pair_facts_invalidate_result(self):
        self.match.decision = 'refused'
        self.match.candidate_facts = {'licences_not_held_at_start': ['B']}
        # QuerySet update deliberately bypasses validation to exercise fingerprinting only.
        CandidateOfferMatch.objects.filter(pk=self.match.pk).update(
            decision='refused', candidate_facts=self.match.candidate_facts
        )
        self.assertEqual(search_queue.search_rows()['offers'][0]['reason'], 'pending')

    def test_all_refused_matches_need_external_search(self):
        self.match.decision = 'refused'
        self.match.save(update_fields=['decision'])
        rows = search_queue.search_rows()
        self.assertEqual(rows['offers'][0]['reason'], 'refused')
        self.assertEqual(rows['candidates'][0]['reason'], 'refused')

    def test_retained_match_is_not_external_search_work(self):
        self.match.decision = 'retained'
        self.match.save(update_fields=['decision'])
        self.assertEqual(search_queue.search_rows(), {'offers': [], 'candidates': []})
        self.assertEqual(self.client.get(self.offer_url).status_code, 302)

    def test_incomplete_offer_is_explicit(self):
        self.offer.validated_at = None
        self.offer.data = {'title': 'Incomplete fictional offer'}
        self.offer.save()
        self.assertEqual(
            search_queue.search_rows()['offers'][0]['reason'], 'incomplete'
        )

    def test_unverified_or_inactive_candidate_is_not_matched(self):
        self.candidate.email_verified_at = None
        self.candidate.save()
        self.assertEqual(
            search_queue.search_rows()['offers'][0]['reason'], 'no_candidates'
        )
        self.assertEqual(search_queue.search_rows()['candidates'], [])
        self.assertEqual(self.client.get(self.candidate_url).status_code, 404)

    def test_followup_is_shared_and_date_is_retained(self):
        self.offer.delete()
        due = timezone.localdate()
        self.assertEqual(
            self.client.post(
                self.candidate_url, {'searching': 'on', 'follow_up_on': due.isoformat()}
            ).status_code,
            302,
        )
        obj = CandidateSupport.objects.get(candidate_profile=self.candidate)
        self.assertEqual(obj.updated_by_adviser, self.adviser)
        self.assertEqual(obj.follow_up_on, due)
        self.assertTrue(search_queue.search_rows()['candidates'][0]['due'])
        other = User.objects.create_user(
            'other-adviser@example.invalid', kind='adviser'
        )
        self.client.force_login(other)
        response = self.client.get(self.candidate_url)
        self.assertContains(response, 'value="' + due.isoformat() + '"')
        self.assertContains(response, 'checked')
        self.assertEqual(self.client.post(self.candidate_url, {}).status_code, 302)
        obj.refresh_from_db()
        self.assertFalse(obj.is_searching)
        self.assertIsNone(obj.follow_up_on)
        self.assertEqual(obj.updated_by_adviser, other)

    def test_future_followup_is_visible_but_has_no_red_count(self):
        self.offer.delete()
        CandidateSupport.objects.create(
            candidate_profile=self.candidate,
            is_searching=True,
            follow_up_on=timezone.localdate() + timedelta(days=1),
            updated_by_adviser=self.adviser,
        )
        response = self.client.get(self.url, {'view': 'candidates'})
        self.assertEqual(response.context['queue_navigation'][2]['count'], 0)
        self.assertContains(response, self.candidate.display_name)
        self.assertNotContains(response, 'class="adviser-action-count"')
        detail = self.client.get(self.candidate_url)
        self.assertEqual(detail.context['queue_navigation'][2]['count'], 0)

    def test_due_followup_and_search_without_date_are_counted(self):
        self.offer.delete()
        followup = CandidateSupport.objects.create(
            candidate_profile=self.candidate,
            is_searching=True,
            follow_up_on=timezone.localdate(),
            updated_by_adviser=self.adviser,
        )
        for day in (
            timezone.localdate(),
            timezone.localdate() - timedelta(days=1),
            None,
        ):
            followup.follow_up_on = day
            followup.save()
            response = self.client.get(self.url, {'view': 'candidates'})
            self.assertEqual(response.context['queue_navigation'][2]['count'], 1)
            self.assertContains(response, 'aria-label="1 action à traiter"')
            self.assertEqual(
                self.client.get(self.candidate_url).context['queue_navigation'][2][
                    'count'
                ],
                1,
            )

    def test_invalid_followup_does_not_write(self):
        self.offer.delete()
        response = self.client.post(self.candidate_url, {'follow_up_on': '2026-12-01'})
        self.assertContains(response, 'Commencez la recherche')
        self.assertFalse(CandidateSupport.objects.exists())
        self.client.post(
            self.candidate_url, {'searching': 'on', 'follow_up_on': 'bad-date'}
        )
        self.assertFalse(CandidateSupport.objects.exists())

    def test_permissions_and_csrf(self):
        self.offer.delete()
        for user in (self.candidate.user, prepared_user('employer')):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.candidate_url).status_code, 403)
            self.assertEqual(
                self.client.post(self.candidate_url, {'searching': 'on'}).status_code,
                403,
            )
        self.client.logout()
        self.assertEqual(self.client.get(self.candidate_url).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.adviser)
        self.assertEqual(
            csrf.post(self.candidate_url, {'searching': 'on'}).status_code, 403
        )
        self.assertFalse(CandidateSupport.objects.exists())

    def test_each_support_requires_a_unique_target(self):
        for model, field, target in (
            (JobOfferSupport, 'job_offer', self.offer),
            (CandidateSupport, 'candidate_profile', self.candidate),
        ):
            with self.subTest(model=model.__name__):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.create(updated_by_adviser=self.adviser)
                model.objects.create(**{field: target}, updated_by_adviser=self.adviser)
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.create(
                        **{field: target}, updated_by_adviser=self.adviser
                    )

    def test_offer_support_is_shared_between_advisers(self):
        self.candidate.delete()
        due = timezone.localdate()
        self.client.post(self.offer_url, {'searching': 'on', 'follow_up_on': due})
        support = JobOfferSupport.objects.get(job_offer=self.offer)
        other = User.objects.create_user('second@support.invalid', kind='adviser')
        self.client.force_login(other)
        self.assertContains(self.client.get(self.offer_url), 'checked')
        self.client.post(self.offer_url, {})
        support.refresh_from_db()
        self.assertFalse(support.is_searching)
        self.assertEqual(support.updated_by_adviser, other)
        self.assertEqual(JobOfferSupport.objects.count(), 1)
        self.assertFalse(CandidateSupport.objects.exists())

    def test_translations(self):
        self.offer.delete()
        for language, title in [
            ('fr', 'Candidats sans offre'),
            ('en', 'Candidates without an offer'),
            ('de', 'Kandidaten ohne Stellenangebot'),
        ]:
            self.assertContains(
                self.client.get(self.url, {'lang': language, 'view': 'candidates'}),
                title,
            )
