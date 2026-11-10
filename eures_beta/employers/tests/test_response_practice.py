import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.employers.models import (
    Company,
    CompanyMembership,
    EmployerProfile,
)

User = get_user_model()


class ResponsePracticeTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            email='one@example.invalid', kind='employer'
        )
        self.colleague = User.objects.create_user(
            email='two@example.invalid', kind='employer'
        )
        company = Company.objects.create(name='Fictional shared establishment')
        for person in (self.employer, self.colleague):
            CompanyMembership.objects.create(company=company, person=person)
        self.client.force_login(self.employer)
        self.url = reverse('employer_response_practice')

    def save(self, **changes):
        values = {
            'revision': 0,
            'response_coverage': 'all',
            'response_time': 'one_two_weeks',
        }
        values.update(changes)
        return self.client.post(
            self.url, json.dumps(values), content_type='application/json', secure=True
        )

    def test_save_reload_and_update_same_record(self):
        self.assertEqual(self.client.get(self.url, secure=True).json()['revision'], 0)
        first = self.save()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['revision'], 1)
        self.client.logout()
        self.client.force_login(self.employer)
        self.assertEqual(self.client.get(self.url, secure=True).json(), first.json())
        result = self.save(
            revision=1, response_coverage='selected', response_time='variable'
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['revision'], 2)
        self.assertEqual(EmployerProfile.objects.count(), 1)
        saved = EmployerProfile.objects.get()
        self.assertEqual(saved.user_id, self.employer.pk)
        self.assertEqual(self.employer.employer_profile.pk, saved.pk)
        self.assertEqual(saved.response_time, 'variable')
        self.assertGreaterEqual(saved.updated, saved.created)

    def test_colleagues_have_independent_answers_and_cannot_target_each_other(self):
        self.save()
        self.client.force_login(self.colleague)
        self.assertEqual(self.client.get(self.url, secure=True).json()['revision'], 0)
        response = self.save(
            employer_id=self.employer.pk,
            response_coverage='varies',
            response_time='over_month',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EmployerProfile.objects.get(user=self.employer).response_time,
            'one_two_weeks',
        )
        self.assertEqual(
            EmployerProfile.objects.get(user=self.colleague).response_time,
            'over_month',
        )

    def test_invalid_and_partial_answers_never_write(self):
        for changes in (
            {'response_time': ''},
            {'response_coverage': ''},
            {'response_time': '7'},
            {'response_coverage': 'everyone'},
            {'revision': True},
            {'revision': '0'},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.save(**changes).status_code, 400)
        for payload in ('[]', 'null', 'broken', '"' + ('x' * 4097) + '"'):
            self.assertEqual(
                self.client.post(
                    self.url, payload, content_type='application/json', secure=True
                ).status_code,
                400,
            )
        self.assertFalse(EmployerProfile.objects.exists())
        self.save()
        self.assertEqual(self.save(revision=1, response_time='bogus').status_code, 400)
        self.assertEqual(EmployerProfile.objects.get().response_time, 'one_two_weeks')

    def test_stale_write_cannot_overwrite_saved_answers(self):
        self.save()
        self.assertEqual(self.save(response_time='over_month').status_code, 409)
        self.save(revision=1, response_time='under_week')
        self.assertEqual(
            self.save(revision=1, response_time='over_month').status_code, 409
        )
        self.assertEqual(EmployerProfile.objects.get().response_time, 'under_week')

    def test_access_requires_active_employer_in_every_environment(self):
        adviser = User.objects.create_user(
            email='adviser@example.invalid', kind='adviser'
        )
        candidate = User.objects.create_user(
            email='candidate@example.invalid', kind='candidate'
        )
        for user in (None, adviser, candidate):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(self.url, secure=True).status_code, 403)
            self.assertEqual(self.save().status_code, 403)
        self.employer.is_active = False
        self.employer.save()
        self.client.force_login(self.employer)
        self.assertEqual(self.save().status_code, 403)
        self.employer.is_active = True
        self.employer.save()
        self.client.force_login(self.employer)
        self.assertFalse(EmployerProfile.objects.exists())
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                self.settings(
                    DJANGO_ENVIRONMENT=environment,
                    EMAIL_DELIVERY_ENABLED=True,
                ),
            ):
                response = self.client.get(self.url, REMOTE_ADDR='192.0.2.1')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    self.save(revision=response.json()['revision']).status_code, 200
                )

    def test_csrf_and_methods(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.employer)
        self.assertEqual(client.post(self.url, {}, secure=True).status_code, 403)
        self.assertEqual(self.client.delete(self.url, secure=True).status_code, 405)
        self.assertFalse(EmployerProfile.objects.exists())

    def test_database_rejects_duplicate_and_noncanonical_answers(self):
        self.save()
        for values in (
            {
                'user': self.employer,
                'response_coverage': 'all',
                'response_time': 'under_week',
            },
            {
                'user': self.colleague,
                'response_coverage': 'bogus',
                'response_time': 'under_week',
            },
            {
                'user': self.colleague,
                'response_coverage': 'all',
                'response_time': 'bogus',
            },
        ):
            with (
                self.subTest(values=values),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                EmployerProfile.objects.create(**values)
        adviser = User.objects.create_user(
            email='another@example.invalid', kind='adviser'
        )
        with self.assertRaises(ValidationError):
            EmployerProfile(
                user=adviser, response_coverage='all', response_time='under_week'
            ).full_clean()

    def test_questions_then_summary_in_both_layouts_and_three_languages(self):
        for language, label, button in (
            (
                'fr',
                'Répondez-vous à toutes les candidatures reçues ?',
                'Modifier mes réponses',
            ),
            ('en', 'Do you reply to all applications received?', 'Change my answers'),
            (
                'de',
                'Antworten Sie auf alle eingegangenen Bewerbungen?',
                'Meine Antworten ändern',
            ),
        ):
            for prefix in ('import-',):
                path = f'/employer/pages/{prefix}{language}.html'
                page = self.client.get(path, secure=True)
                self.assertContains(page, label)
                self.assertContains(page, button)
                self.assertContains(page, 'id="response-practice-summary" hidden')
                self.assertNotContains(page, 'id="response-practice-form" hidden')
        self.save()
        for prefix in ('import-',):
            page = self.client.get(f'/employer/pages/{prefix}fr.html', secure=True)
            self.assertContains(page, 'Oui, à toutes les candidatures')
            self.assertContains(page, 'Entre 1 et 2 semaines')
            self.assertContains(page, 'id="response-practice-form" hidden')
            self.assertContains(page, 'value="one_two_weeks" selected')
        self.client.force_login(self.colleague)
        page = self.client.get('/employer/pages/import-fr.html', secure=True)
        self.assertContains(page, 'id="response-practice-summary" hidden')
        self.assertNotContains(page, 'value="one_two_weeks" selected')
