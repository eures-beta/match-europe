from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, RequestFactory

from eures_beta.candidates.models import CandidateProfile


class CandidateProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'candidate@example.test', kind='candidate'
        )

    def profile(self, **changes):
        values = dict(
            user=self.user,
            display_name='Fictional candidate',
            desired_occupations='Fictional job',
            desired_countries=['FR'],
            mobility='move',
            availability='now',
            contract_types=['permanent'],
            working_time=['full'],
            schedule_preference='varied',
            working_conditions=['discuss'],
            salary_preference='discuss',
        )
        return CandidateProfile(**(values | changes))

    def test_round_trip_and_conditional_cleanup(self):
        profile = self.profile(
            language_skills={
                'status': 'specified',
                'languages': [{'code': 'de', 'level': 'B1'}],
            },
            commute_time='1h',
            transport_modes=['car'],
            salary_amount=Decimal('1500.00'),
        )
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.language_skills['languages'][0]['level'], 'B1')
        self.assertEqual(profile.commute_time, '')
        self.assertEqual(profile.transport_modes, [])
        self.assertIsNone(profile.salary_amount)
        self.assertEqual(profile.occupation_references, [])
        self.assertEqual(self.user.candidate_profile.pk, profile.pk)
        self.assertEqual(str(profile), str(profile.pk))

    def test_one_profile_per_account(self):
        self.profile().save()
        with self.assertRaises(ValidationError):
            self.profile().save()

    def test_wrong_roles_rejected(self):
        for kind in ('employer', 'adviser'):
            user = get_user_model().objects.create_user(
                kind + '@example.test', kind=kind
            )
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                self.profile(user=user).save()

    def test_invalid_answers_rejected(self):
        for changes in (
            {'desired_countries': ['XX']},
            {'occupation_references': ['rome:INVALID']},
            {'salary_preference': 'minimum'},
            {'availability': 'date'},
            {'mobility': 'commute'},
            {'schedule_preference': 'specific'},
            {'language_skills': {'status': 'specified', 'languages': []}},
            {'contract_types': ['permanent', 'discuss']},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.profile(**changes).save()
        self.assertEqual(CandidateProfile.objects.count(), 0)

    def test_salary_and_schedule_round_trip(self):
        profile = self.profile(
            salary_preference='minimum',
            salary_amount=Decimal('2500.50'),
            salary_currency='EUR',
            salary_period='month',
            salary_basis='gross',
            schedule_preference='specific',
            schedule_monday=['morning'],
            schedule_strict=True,
            working_conditions=['day'],
        )
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.salary_amount, Decimal('2500.50'))
        self.assertEqual(profile.schedule_monday, ['morning'])
        profile.working_conditions = ['night']
        with self.assertRaises(ValidationError):
            profile.save()

    def test_database_constraints_and_account_deletion(self):
        profile = self.profile()
        profile.save()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            CandidateProfile.objects.filter(pk=profile.pk).update(language='xx')
        with transaction.atomic(), self.assertRaises(IntegrityError):
            CandidateProfile.objects.filter(pk=profile.pk).update(salary_amount=-1)
        self.user.delete()
        self.assertFalse(CandidateProfile.objects.exists())

    def test_database_rejects_bypassing_account_role_validation(self):
        profile = self.profile()
        profile.save()
        employer = get_user_model().objects.create_user(
            'employer@example.test', kind='employer'
        )
        with transaction.atomic(), self.assertRaises(IntegrityError):
            CandidateProfile.objects.filter(pk=profile.pk).update(user=employer)

    def test_admin_only_exposes_metadata(self):
        profile = self.profile()
        profile.save()
        operator = get_user_model().objects.create_superuser(
            'operator@example.test', kind='adviser'
        )
        request = RequestFactory().get('/admin/')
        request.user = operator
        model_admin = admin.site._registry[CandidateProfile]
        self.assertEqual(model_admin.list_display, ('id', 'created_at', 'updated_at'))
        self.assertTrue(model_admin.has_view_permission(request))
        self.assertFalse(model_admin.has_view_permission(request, profile))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, profile))
        self.assertFalse(model_admin.has_delete_permission(request, profile))
