from io import StringIO
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.core.management import call_command, CommandError
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from eures_beta.users.test_accounts import prepared_user
from eures_beta.matching import team_services, services
from eures_beta.matching.models import (
    MatchPair,
    MatchingTeam,
    TeamMembership,
    TeamCandidate,
    TeamOffer,
    MatchDecision,
    MatchEvaluation,
)

SETTINGS = dict(
    MATCHING_LOCAL_ENABLED=True,
    MATCHING_TEAMS_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    SHARED_DEMO=False,
    REQUEST_METRICS_ENABLED=False,
)


@override_settings(**SETTINGS)
class TeamTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_matching_teams', stdout=StringIO())

    def setUp(self):
        self.a = prepared_user('adviser')
        self.b = prepared_user('matching-peer')
        self.other = prepared_user('matching-other')
        self.team = MatchingTeam.objects.get(slug='trial-main')
        self.client.force_login(self.a)

    def pair(self, key='manual-zero'):
        return MatchPair.objects.select_related('candidate', 'offer', 'team').get(
            candidate__user__email=key + '@matching-trial.invalid'
        )

    def detail(self, pair):
        return reverse('matching_team_detail', args=[pair.pk])

    def post(
        self,
        pair,
        *,
        action='manual',
        reason='Professional fit confirmed for review.',
        **extra,
    ):
        previous = pair.decisions.order_by('-id').first()
        payload = dict(
            action=action,
            reason=reason,
            evaluation=pair.evaluations.latest('id').pk,
            decision_version=previous.pk if previous else 0,
        )
        payload.update(extra)
        return self.client.post(self.detail(pair), payload)

    def test_shared_dashboard_and_other_team_isolation(self):
        for person in (self.a, self.b):
            self.client.force_login(person)
            page = self.client.get(reverse('dashboard'))
            self.assertContains(page, 'Profil fictif F')
            self.assertNotContains(page, 'Offre fictive - autre equipe')
            self.assertNotContains(page, 'Profil fictif - autre equipe')
        self.client.force_login(self.other)
        page = self.client.get(reverse('dashboard'))
        self.assertContains(page, 'Offre fictive - autre equipe')
        self.assertNotContains(page, 'Profil fictif F')
        pair = self.pair()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)
        self.assertEqual(self.post(pair).status_code, 404)
        self.assertEqual(
            self.client.get(
                reverse('matching_team_manual', args=[self.team.pk])
            ).status_code,
            403,
        )

    def test_zero_score_manual_retention_has_reason_author_team_and_unchanged_score(
        self,
    ):
        pair = self.pair()
        evaluation = pair.evaluations.latest('id')
        self.assertEqual(evaluation.result['established'], 0)
        self.assertFalse(evaluation.result['blocked'])
        self.assertEqual(self.post(pair, reason='').status_code, 400)
        self.assertFalse(pair.decisions.exists())
        self.assertEqual(self.post(pair, action='retained').status_code, 400)
        self.assertEqual(self.post(pair).status_code, 302)
        event = pair.decisions.latest('id')
        self.assertTrue(event.manual)
        self.assertEqual(event.decided_by, self.a)
        self.assertEqual(event.team, self.team)
        self.assertTrue(event.reason)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.result['established'], 0)
        pair.refresh_from_db()
        self.assertEqual(pair.decision, 'retained')

    def test_manual_cannot_bypass_any_of_the_three_blocking_conditions(self):
        for key in ('date', 'schedule', 'permit'):
            pair = self.pair(key)
            self.assertEqual(self.post(pair).status_code, 400)
            self.assertFalse(pair.decisions.exists())

    def test_manual_preparation_reuses_existing_pair_and_stamps_authenticated_author(
        self,
    ):
        pair = self.pair()
        count = MatchPair.objects.count()
        endpoint = reverse('matching_team_manual', args=[self.team.pk])
        response = self.client.post(
            endpoint, {'candidate': pair.candidate_id, 'offer': pair.offer_id}
        )
        self.assertRedirects(
            response, self.detail(pair) + '?lang=fr', fetch_redirect_response=False
        )
        self.assertEqual(MatchPair.objects.count(), count)
        evaluation = pair.evaluations.latest('id')
        self.assertEqual(evaluation.requested_by, self.a)
        self.assertEqual(evaluation.request_mode, 'manual')
        self.assertFalse(pair.decisions.exists())

    def test_manual_preparation_rejects_cross_team_candidate_and_offer_ids(self):
        outside = self.pair('outside')
        pair = self.pair()
        endpoint = reverse('matching_team_manual', args=[self.team.pk])
        before = MatchEvaluation.objects.count()
        for payload in (
            {'candidate': outside.candidate_id, 'offer': pair.offer_id},
            {'candidate': pair.candidate_id, 'offer': outside.offer_id},
        ):
            self.assertEqual(self.client.post(endpoint, payload).status_code, 400)
        self.assertEqual(MatchEvaluation.objects.count(), before)
        with self.assertRaises(PermissionDenied):
            team_services.calculate(
                self.a, self.team.pk, outside.candidate_id, pair.offer_id, manual=True
            )

    def test_peer_sees_reason_and_recalculation_preserves_decision(self):
        pair = self.pair()
        self.post(pair, reason='Specific professional opportunity.')
        self.client.force_login(self.b)
        page = self.client.get(self.detail(pair))
        self.assertContains(page, 'Specific professional opportunity.')
        self.assertContains(page, 'Conseiller A')
        self.assertEqual(
            self.client.post(self.detail(pair), {'action': 'calculate'}).status_code,
            302,
        )
        pair.refresh_from_db()
        self.assertEqual(pair.decision, 'retained')
        self.assertEqual(pair.decisions.count(), 1)
        page = self.client.get(self.detail(pair))
        self.assertTrue(page.context['decision_outdated'])
        self.assertEqual(pair.evaluations.latest('id').requested_by, self.b)

    def test_stale_answers_and_concurrent_decisions_are_rejected(self):
        pair = self.pair()
        evaluation = pair.evaluations.latest('id')
        self.post(pair)
        self.client.force_login(self.b)
        response = self.post(pair, action='refused', decision_version=0)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(pair.decisions.count(), 1)
        pair.offer.revision += 1
        pair.offer.save(update_fields=['revision'])
        self.assertEqual(self.post(pair, evaluation=evaluation.pk).status_code, 409)
        self.assertEqual(pair.decisions.count(), 1)

    def test_duplicate_manual_post_is_idempotent(self):
        pair = self.pair()
        self.assertEqual(self.post(pair, decision_version=0).status_code, 302)
        self.assertEqual(self.post(pair, decision_version=0).status_code, 302)
        self.assertEqual(pair.decisions.count(), 1)

    def test_revoked_membership_and_readonly_members_cannot_mutate(self):
        pair = self.pair()
        member = TeamMembership.objects.get(user=self.a, team=self.team)
        member.can_decide = False
        member.save()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 200)
        self.assertEqual(self.post(pair).status_code, 403)
        self.assertEqual(
            self.client.post(self.detail(pair), {'action': 'calculate'}).status_code,
            403,
        )
        member.active = False
        member.save()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)
        with self.assertRaises(PermissionDenied):
            team_services.calculate(
                self.a, self.team.pk, pair.candidate_id, pair.offer_id
            )

    def test_revoked_candidate_or_offer_assignment_hides_pair(self):
        pair = self.pair()
        grant = TeamCandidate.objects.get(team=self.team, candidate=pair.candidate)
        grant.delete()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)
        with self.assertRaises(PermissionDenied):
            team_services.decide(
                self.a,
                pair.pk,
                pair.evaluations.latest('id').pk,
                'retained',
                manual=True,
                reason='x',
            )
        TeamCandidate.objects.create(team=self.team, candidate=pair.candidate)
        TeamOffer.objects.filter(offer=pair.offer).delete()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)

    def test_inactive_team_and_wrong_roles_are_denied(self):
        pair = self.pair()
        self.team.active = False
        self.team.save()
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Profil fictif F')
        self.client.force_login(prepared_user('employer'))
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 403)

    def test_csrf_and_get_do_not_record_a_decision(self):
        pair = self.pair()
        self.client.get(self.detail(pair), {'action': 'manual', 'reason': 'x'})
        self.assertFalse(pair.decisions.exists())
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.a)
        self.assertEqual(
            strict.post(self.detail(pair), {'action': 'manual'}).status_code, 403
        )

    def test_legacy_operator_routes_do_not_bypass_team_access(self):
        pair = self.pair()
        self.client.logout()
        self.assertRedirects(
            self.client.get(reverse('matching_local')),
            reverse('dashboard'),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.get(reverse('matching_detail', args=[pair.pk])).status_code, 404
        )
        self.assertEqual(self.client.get(self.detail(pair)).status_code, 302)

    def test_remote_team_matching_in_all_environments(self):
        pair = self.pair()
        pair.candidate.user.email = 'candidate@example.org'
        pair.candidate.user.save(update_fields=['email'])
        pair.offer.created_by.email = 'employer@example.org'
        pair.offer.created_by.save(update_fields=['email'])
        pair.offer.email = 'contact@example.org'
        pair.offer.save(update_fields=['email'])
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                    SHARED_DEMO=True,
                ),
            ):
                self.assertEqual(
                    self.client.get(
                        self.detail(pair), REMOTE_ADDR='192.0.2.1'
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.post(
                        self.detail(pair),
                        {'action': 'calculate'},
                        REMOTE_ADDR='192.0.2.1',
                    ).status_code,
                    302,
                )
                self.client.force_login(self.other)
                self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)
                self.client.force_login(self.a)
                with self.assertRaises(CommandError):
                    call_command('seed_matching_teams', stdout=StringIO())
        with override_settings(MATCHING_TEAMS_ENABLED=False):
            self.assertEqual(self.client.get(self.detail(pair)).status_code, 404)

    def test_reason_is_bounded_escaped_and_no_external_call_is_made(self):
        pair = self.pair()
        self.assertEqual(self.post(pair, reason='x' * 2001).status_code, 400)
        with (
            patch('django.core.mail.send_mail') as mail,
            patch('requests.sessions.Session.request') as external,
        ):
            self.assertEqual(
                self.post(pair, reason='<script>bad()</script>').status_code, 302
            )
        page = self.client.get(self.detail(pair))
        self.assertContains(page, '&lt;script&gt;bad()&lt;/script&gt;')
        self.assertNotContains(page, '<script>bad()</script>')
        mail.assert_not_called()
        external.assert_not_called()

    def test_seed_preserves_rejections_and_revoked_memberships(self):
        pair = self.pair()
        self.post(pair, action='refused')
        member = TeamMembership.objects.get(user=self.b, team=self.team)
        member.active = False
        member.save()
        call_command('seed_matching_teams', stdout=StringIO())
        pair.refresh_from_db()
        member.refresh_from_db()
        self.assertEqual(pair.decision, 'refused')
        self.assertFalse(member.active)

    def test_translated_team_pages(self):
        for lang in ('fr', 'en', 'de'):
            self.assertEqual(
                self.client.get(reverse('dashboard'), {'lang': lang}).status_code, 200
            )
            self.assertEqual(
                self.client.get(self.detail(self.pair()), {'lang': lang}).status_code,
                200,
            )
            self.assertEqual(
                self.client.get(
                    reverse('matching_team_manual', args=[self.team.pk]), {'lang': lang}
                ).status_code,
                200,
            )


@override_settings(**SETTINGS)
class TeamConcurrencyTests(TransactionTestCase):
    def test_two_reviewers_cannot_overwrite_each_other_silently(self):
        call_command('seed_matching_teams', stdout=StringIO())
        pair = MatchPair.objects.get(
            candidate__user__email='manual-zero@matching-trial.invalid'
        )
        evaluation = pair.evaluations.latest('id')
        barrier = Barrier(2)

        def review(key):
            close_old_connections()
            try:
                user = prepared_user(key)
                barrier.wait(timeout=10)
                try:
                    team_services.decide(
                        user,
                        pair.pk,
                        evaluation.pk,
                        'retained',
                        manual=True,
                        reason='Review ' + key,
                        expected_decision=0,
                    )
                    return 'saved'
                except services.StaleEvaluation:
                    return 'conflict'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(review, ('adviser', 'matching-peer')))
        self.assertCountEqual(outcomes, ['saved', 'conflict'])
        self.assertEqual(pair.decisions.count(), 1)
