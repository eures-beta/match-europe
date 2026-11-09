from copy import deepcopy
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from eures_beta.matching import engine, services, validation
from eures_beta.matching.models import (
    MatchPair,
    Evaluation,
    Decision,
    OfferRequirements,
)
from eures_beta.candidates.models import CandidateProfile
from eures_beta.employers.models import JobOffer


class EngineTests(SimpleTestCase):
    def run_pair(self, candidate=None, offer=None, requirements=None, facts=None):
        return engine.evaluate(
            candidate or {},
            offer or {},
            requirements or {},
            facts or {},
            today=date(2026, 11, 7),
        )

    def row(self, result, key):
        return next(row for row in result['rows'] if row['key'] == key)

    def test_missing_answers_are_unknown_and_never_block_or_earn_points(self):
        result = self.run_pair()
        self.assertFalse(result['blocked'])
        self.assertEqual(result['established'], 0)
        self.assertEqual(result['unresolved'], 100)
        self.assertEqual(result['status'], 'insufficient')
        self.assertTrue(all(row['state'] == 'unknown' for row in result['rows']))

    def test_unselected_and_learning_skills_are_not_absent_or_mastered(self):
        result = self.run_pair(
            {'acquired_skills': ['a'], 'learning_activities': ['b']},
            {'occupationSkills': {'job': {'skills': ['a', 'b', 'c']}}},
        )
        rows = [row for row in result['rows'] if row['key'] == 'skill']
        self.assertEqual(
            [row['state'] for row in rows], ['match', 'unknown', 'unknown']
        )
        self.assertEqual(rows[1]['reason'], 'learning')
        self.assertAlmostEqual(result['established'], 13.33)
        self.assertFalse(result['blocked'])

    def test_declared_skill_transfers_between_jobs_but_not_from_reference_catalogue(
        self,
    ):
        candidate = {'occupation_skills': {'different_job': {'skills': ['a']}}}
        result = self.run_pair(
            candidate, {'occupationSkills': {'job': {'skills': ['a']}}}
        )
        self.assertEqual(self.row(result, 'skill')['state'], 'match')
        self.assertEqual(
            self.run_pair({}, {'occupation': {'uris': ['job']}})['established'], 0
        )

    def test_alternative_employer_occupations_are_not_merged_as_joint_requirements(
        self,
    ):
        result = self.run_pair(
            {'acquired_skills': ['a', 'b']},
            {'occupationSkills': {'one': {'skills': ['a']}, 'two': {'skills': ['b']}}},
        )
        self.assertEqual(result['established'], 0)
        self.assertTrue(all(row['state'] == 'unknown' for row in result['rows']))

    def test_occupation_and_behaviours_never_add_points(self):
        base = self.run_pair()
        changed = self.run_pair(
            {'desired_occupations': 'Same title', 'professional_behaviours': ['a']},
            {'title': 'Same title', 'occupationSkills': {'job': {'behaviours': ['a']}}},
        )
        self.assertEqual(base, changed)

    def test_date_blocks_only_explicit_mandatory_incompatibility(self):
        candidate = {'availability': 'date', 'available_from': '2026-12-01'}
        for mandatory in (True, False):
            result = self.run_pair(
                candidate,
                requirements={
                    'latest_start': '2026-11-15',
                    'start_mandatory': mandatory,
                },
            )
            self.assertEqual(result['blocked'], mandatory)
        self.assertFalse(
            self.run_pair(
                {'availability': 'month'},
                requirements={'latest_start': '2026-11-15', 'start_mandatory': True},
            )['blocked']
        )

    def test_schedule_requires_explicit_strict_candidate_and_mandatory_offer(self):
        candidate = {
            'schedule_preference': 'specific',
            'schedule_strict': True,
            'schedule_monday': ['morning'],
        }
        requirements = {'schedule': ['saturday:morning'], 'schedule_mandatory': True}
        self.assertTrue(self.run_pair(candidate, requirements=requirements)['blocked'])
        candidate['schedule_strict'] = False
        self.assertFalse(self.run_pair(candidate, requirements=requirements)['blocked'])
        candidate['schedule_strict'] = True
        requirements['schedule_mandatory'] = False
        self.assertFalse(self.run_pair(candidate, requirements=requirements)['blocked'])

    def test_permit_unchecked_is_unknown_and_explicit_absence_can_block(self):
        offer = {'requirements': {'permitRequired': 'yes', 'permits': ['B']}}
        requirements = {'mandatory_permits': ['B']}
        self.assertFalse(
            self.run_pair(offer=offer, requirements=requirements)['blocked']
        )
        self.assertTrue(
            self.run_pair(
                offer=offer,
                requirements=requirements,
                facts={'licences_not_held_at_start': ['B']},
            )['blocked']
        )
        self.assertFalse(
            self.run_pair(
                {'licences_held': ['B']},
                offer,
                requirements,
                {'licences_not_held_at_start': ['B']},
            )['blocked']
        )

    def test_generic_other_permit_never_establishes_compatibility(self):
        result = self.run_pair(
            {'licences_held': ['other']},
            {'requirements': {'permitRequired': 'yes', 'permits': ['other']}},
        )
        self.assertEqual(self.row(result, 'permit')['state'], 'unknown')

    def test_no_requirement_is_not_missing_and_earns_no_bonus(self):
        result = self.run_pair(
            offer={
                'requirements': {'permitRequired': 'no', 'workConditions': ['none']}
            },
            requirements={'languages': []},
        )
        self.assertEqual(self.row(result, 'languages')['state'], 'not_applicable')
        self.assertEqual(self.row(result, 'permits')['state'], 'not_applicable')
        self.assertEqual(result['established'], 0)

    def test_language_mismatch_and_salary_gap_do_not_block(self):
        candidate = {
            'language_skills': {'languages': [{'code': 'fr', 'level': 'A1'}]},
            'salary_preference': 'minimum',
            'salary_amount': 30,
            'salary_period': 'hour',
            'salary_currency': 'EUR',
            'salary_basis': 'gross',
        }
        req = {
            'languages': [{'code': 'fr', 'level': 'B2'}],
            'salary': {
                'maximum': 20,
                'period': 'hour',
                'currency': 'EUR',
                'basis': 'gross',
            },
        }
        result = self.run_pair(candidate, requirements=req)
        self.assertFalse(result['blocked'])
        self.assertEqual(self.row(result, 'language')['state'], 'mismatch')
        self.assertEqual(self.row(result, 'salary')['state'], 'mismatch')
        candidate['salary_amount'] = 15
        self.assertEqual(
            self.row(self.run_pair(candidate, requirements=req), 'salary')['state'],
            'match',
        )
        candidate['salary_basis'] = 'net'
        self.assertEqual(
            self.row(self.run_pair(candidate, requirements=req), 'salary')['state'],
            'unknown',
        )

    def test_monthly_salary_without_common_working_hours_basis_is_unknown(self):
        result = self.run_pair(
            {
                'salary_preference': 'minimum',
                'salary_amount': 2000,
                'salary_period': 'month',
                'salary_currency': 'EUR',
                'salary_basis': 'gross',
            },
            requirements={
                'salary': {
                    'maximum': 3000,
                    'period': 'month',
                    'currency': 'EUR',
                    'basis': 'gross',
                }
            },
        )
        self.assertEqual(self.row(result, 'salary')['state'], 'unknown')

    def test_text_is_never_parsed_into_strict_requirements(self):
        result = self.run_pair(
            offer={
                'clarifications': {
                    'salary': '30 EUR gross per hour',
                    'startDate': 'mandatory tomorrow',
                    'frenchLevel': 'C2',
                }
            }
        )
        self.assertEqual(result['established'], 0)
        self.assertFalse(result['blocked'])

    def test_supplements_reject_unbounded_or_ambiguous_values(self):
        for value in (
            {'start_mandatory': 'false'},
            {'start_mandatory': True},
            {'schedule': ['anytime']},
            {'salary': {'maximum': 'NaN'}},
            {'languages': [{'code': 'fr', 'level': 'fluent'}]},
            {'country': 'France'},
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validation.requirements(value)
        with self.assertRaises(ValidationError):
            validation.candidate_facts({'licences_not_held_at_start': ['B', 'B']})


@override_settings(
    MATCHING_LOCAL_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    SHARED_DEMO=False,
)
class LocalMatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_matching_trial', stdout=StringIO())

    def setUp(self):
        from django.contrib.auth.models import Permission
        from eures_beta.users.models import User

        self.operator = User.objects.create_user(
            'operator@matching-permissions.invalid', kind='adviser'
        )
        self.operator.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label='matching',
                codename__in=['view_matchpair', 'change_matchpair'],
            )
        )
        self.client.force_login(self.operator)

    def pair(self, name='compatible'):
        return MatchPair.objects.select_related('candidate', 'offer').get(
            candidate__user__email=name + '@matching-trial.invalid'
        )

    def test_five_scenarios_and_seed_idempotence(self):
        expected = {
            'compatible': 'review',
            'unknown': 'review',
            'date': 'blocked',
            'schedule': 'blocked',
            'permit': 'blocked',
        }
        for key, state in expected.items():
            self.assertEqual(
                self.pair(key).evaluations.latest('id').result['status'], state
            )
        call_command('seed_matching_trial', stdout=StringIO())
        self.assertEqual(MatchPair.objects.count(), 5)
        self.assertEqual(Evaluation.objects.count(), 5)

    def test_post_calculates_real_models_without_mutating_profile_or_offer(self):
        pair = self.pair()
        before = deepcopy(pair.offer.data)
        with (
            patch('django.core.mail.send_mail') as mail,
            patch('requests.sessions.Session.request') as external,
        ):
            response = self.client.post(
                reverse('matching_local'),
                {'candidate': pair.candidate_id, 'offer': pair.offer_id},
            )
        self.assertEqual(response.status_code, 302)
        pair.offer.refresh_from_db()
        self.assertEqual(pair.offer.data, before)
        self.assertEqual(pair.evaluations.count(), 2)
        mail.assert_not_called()
        external.assert_not_called()

    def test_human_refusal_survives_recalculation_and_duplicate_post(self):
        pair = self.pair()
        evaluation = pair.evaluations.latest('id')
        services.decide(pair.pk, evaluation.pk, 'refused')
        services.decide(pair.pk, evaluation.pk, 'refused')
        self.assertEqual(Decision.objects.count(), 1)
        services.calculate(pair.candidate, pair.offer)
        pair.refresh_from_db()
        self.assertEqual(pair.decision, 'refused')
        self.assertEqual(pair.evaluations.count(), 2)

    def test_blocked_pair_cannot_be_retained(self):
        pair = self.pair('date')
        with self.assertRaises(ValueError):
            services.decide(pair.pk, pair.evaluations.latest('id').pk, 'retained')
        self.assertEqual(Decision.objects.count(), 0)

    def test_latest_evaluation_and_current_answers_required(self):
        pair = self.pair()
        old = pair.evaluations.latest('id')
        new = services.calculate(pair.candidate, pair.offer)
        with self.assertRaises(services.StaleEvaluation):
            services.decide(pair.pk, old.pk, 'retained')
        pair.offer.revision += 1
        pair.offer.save(update_fields=['revision'])
        with self.assertRaises(services.StaleEvaluation):
            services.decide(pair.pk, new.pk, 'retained')
        response = self.client.post(
            reverse('matching_detail', args=[pair.pk]),
            {'action': 'retained', 'evaluation': new.pk},
        )
        self.assertEqual(response.status_code, 409)

    def test_profile_and_requirement_changes_invalidate_the_result(self):
        pair = self.pair()
        old = pair.evaluations.latest('id')
        pair.candidate.salary_amount = 50
        pair.candidate.save()
        with self.assertRaises(services.StaleEvaluation):
            services.decide(pair.pk, old.pk, 'retained')
        new = services.calculate(pair.candidate, pair.offer)
        supplement = pair.offer.matching_requirements
        supplement.data['country'] = 'DE'
        supplement.save()
        with self.assertRaises(services.StaleEvaluation):
            services.decide(pair.pk, new.pk, 'retained')

    def test_csrf_get_and_unknown_actions_never_change_a_decision(self):
        pair = self.pair()
        path = reverse('matching_detail', args=[pair.pk])
        self.client.get(path, {'action': 'retained'})
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(path, {'action': 'refused'})
            .status_code,
            403,
        )
        self.assertEqual(self.client.post(path, {'action': 'send'}).status_code, 400)
        self.assertEqual(Decision.objects.count(), 0)

    def test_all_environments_and_remote_clients_keep_explicit_permissions(self):
        path = reverse('matching_local')
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                    LOGIN_EMAIL_ENABLED=True,
                    SHARED_DEMO=True,
                ),
            ):
                self.assertEqual(
                    self.client.get(path, REMOTE_ADDR='192.0.2.1').status_code, 200
                )
                pair = self.pair()
                self.assertEqual(
                    self.client.post(
                        path,
                        {'candidate': pair.candidate_id, 'offer': pair.offer_id},
                        REMOTE_ADDR='192.0.2.1',
                    ).status_code,
                    302,
                )
                with self.assertRaises(CommandError):
                    call_command('seed_matching_trial', stdout=StringIO())
        with override_settings(MATCHING_LOCAL_ENABLED=False):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(path).status_code, 403)
        self.client.force_login(self.pair().candidate.user)
        self.assertEqual(self.client.get(path).status_code, 403)
        self.client.force_login(self.operator)
        self.operator.user_permissions.clear()
        self.assertEqual(self.client.get(path).status_code, 403)

    def test_inactive_objects_are_hidden_and_real_addresses_are_eligible(self):
        pair = self.pair()
        user = pair.candidate.user
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(
            self.client.get(reverse('matching_detail', args=[pair.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                reverse('matching_local'),
                {'candidate': pair.candidate_id, 'offer': pair.offer_id},
            ).status_code,
            400,
        )
        user.is_active = True
        user.email = 'hidden@example.com'
        user.save(update_fields=['is_active', 'email'])
        self.assertEqual(
            self.client.get(reverse('matching_detail', args=[pair.pk])).status_code, 200
        )

    def test_result_contains_no_contacts_or_raw_profile_snapshot(self):
        pair = self.pair()
        result = pair.evaluations.latest('id').result
        self.assertNotIn('email', str(result))
        self.assertNotIn('display_name', str(result))
        self.assertNotIn('candidate_snapshot', result)
        response = self.client.get(reverse('matching_detail', args=[pair.pk]))
        self.assertNotContains(response, pair.candidate.user.email)
        self.assertNotContains(response, pair.offer.email)

    def test_translated_pages_show_states_and_not_only_colours(self):
        titles = {
            'fr': 'Matching local',
            'en': 'Local matching',
            'de': 'Lokales Matching',
        }
        for language, title in titles.items():
            response = self.client.get(reverse('matching_local'), {'lang': language})
            self.assertContains(response, title)
            pair = self.pair('date')
            response = self.client.get(
                reverse('matching_detail', args=[pair.pk]), {'lang': language}
            )
            self.assertContains(response, 'main-content')
            self.assertContains(response, 'name="evaluation"')
            self.assertNotContains(response, 'name="action" value="send"')

    def test_reconfirmation_is_a_new_event_for_a_new_evaluation(self):
        pair = self.pair()
        first = pair.evaluations.latest('id')
        services.decide(pair.pk, first.pk, 'retained')
        second = services.calculate(pair.candidate, pair.offer)
        services.decide(pair.pk, second.pk, 'retained')
        self.assertEqual(pair.decisions.count(), 2)
        self.assertEqual(pair.decisions.latest('id').evaluation_id, second.pk)

    def test_explanations_include_the_compared_values(self):
        pair = self.pair()
        result = services.calculate(pair.candidate, pair.offer).result
        rows = {row['key']: row for row in result['rows']}
        self.assertEqual(rows['language']['expected'], 'A2')
        self.assertEqual(rows['language']['declared'], 'B1')
        self.assertEqual(rows['schedule']['expected'], 'saturday:morning')
        self.assertEqual(rows['salary']['expected'], '22')
        self.assertEqual(rows['salary']['declared'], '18.00')
        response = self.client.get(reverse('matching_detail', args=[pair.pk]))
        self.assertContains(response, 'Samedi')
        self.assertContains(response, 'Français')
        self.assertContains(response, 'Mobilité')
        self.assertNotContains(response, 'saturday:morning')
        self.assertNotContains(response, 'weekend</h4>')

    def test_matching_models_are_metadata_only_in_readonly_admin(self):
        from django.contrib.auth import get_user_model
        from django.contrib import admin
        from eures_beta.users.admin_base import MetadataOnlyAdmin

        person = get_user_model().objects.create_user(
            'operator@example.invalid', kind='adviser', is_staff=True, is_superuser=True
        )
        self.client.force_login(person)
        pair = self.pair()
        for obj in (
            pair,
            pair.evaluations.latest('id'),
            pair.offer.matching_requirements,
        ):
            self.assertIsInstance(admin.site._registry[type(obj)], MetadataOnlyAdmin)
            name = obj._meta.model_name
            self.assertEqual(
                self.client.post(f'/admin/matching/{name}/add/', {}).status_code, 403
            )
            self.assertEqual(
                self.client.post(
                    f'/admin/matching/{name}/{obj.pk}/change/', {}
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    f'/admin/matching/{name}/{obj.pk}/delete/', {}
                ).status_code,
                403,
            )

    def test_result_list_shows_persisted_scores_and_flags_stale_data_without_recalculation(
        self,
    ):
        pair = self.pair('date')
        evaluation = pair.evaluations.latest('id')
        before = Evaluation.objects.count()
        pair.offer.revision += 1
        pair.offer.save(update_fields=['revision'])
        response = self.client.get(reverse('matching_local'), {'lang': 'fr'})
        self.assertContains(response, 'Résultats du matching')
        self.assertContains(response, 'Évaluation périmée')
        self.assertContains(response, 'Bloqué pour cette offre')
        entry = next(
            item for item in response.context['entries'] if item['pair'].pk == pair.pk
        )
        self.assertEqual(
            entry['result']['established'], evaluation.result['established']
        )
        self.assertTrue(entry['stale'])
        self.assertEqual(Evaluation.objects.count(), before)
        self.assertEqual(Decision.objects.count(), 0)

    def test_detail_score_is_visible_without_an_expand_action(self):
        pair = self.pair('unknown')
        response = self.client.get(
            reverse('matching_detail', args=[pair.pk]), {'lang': 'fr'}
        )
        self.assertContains(response, 'Score global')
        self.assertContains(response, 'Détail du score')
        self.assertContains(response, 'Points à confirmer')
        self.assertContains(response, 'Points forts')
        self.assertContains(response, 'Incompatibilités explicites')
        self.assertNotContains(response, '<details')
        self.assertTrue(response.context['result']['unknowns'])
        self.assertTrue(response.context['result']['strengths'])
