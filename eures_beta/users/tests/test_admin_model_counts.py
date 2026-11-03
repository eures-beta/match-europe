from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from eures_beta.users.models import User


@override_settings(LANGUAGE_CODE='en')
class AdminModelCountsTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            'operator@example.invalid', kind='adviser'
        )
        self.staff = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        User.objects.create_user('employer@example.invalid', kind='employer')
        self.client.force_login(self.superuser)

    def test_default_and_unrecognized_values_do_not_count(self):
        for parameters in ({}, {'model_counts': '0'}, {'model_counts': 'true'}):
            with (
                self.subTest(parameters=parameters),
                CaptureQueriesContext(connection) as queries,
            ):
                response = self.client.get(reverse('admin:index'), parameters)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Show record counts')
            self.assertFalse(any('COUNT(' in query['sql'].upper() for query in queries))

    def test_requested_counts_include_zero_and_persist_until_disabled(self):
        response = self.client.get(reverse('admin:index'), {'model_counts': '1'})
        self.assertContains(response, 'Hide record counts')
        self.assertContains(response, 'Users (3)')
        self.assertContains(response, 'Employer invitations (0)')
        # Do not mutate the app list shared with Django's navigation sidebar.
        for app in response.context['app_list']:
            for model in app['models']:
                self.assertNotIn(' (', str(model['name']))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Hide record counts')
        self.assertContains(response, 'Users (3)')
        self.assertTrue(any('COUNT(' in query['sql'].upper() for query in queries))
        self.client.get(reverse('admin:index'), {'model_counts': '0'})
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Show record counts')
        self.assertFalse(any('COUNT(' in query['sql'].upper() for query in queries))

    def test_preference_is_private_to_session_and_cleared_on_logout(self):
        from django.test import Client

        self.client.get(reverse('admin:index'), {'model_counts': '1'})
        other = Client()
        other.force_login(self.superuser)
        self.assertContains(other.get(reverse('admin:index')), 'Show record counts')
        self.client.logout()
        self.client.force_login(self.superuser)
        self.assertContains(
            self.client.get(reverse('admin:index')), 'Show record counts'
        )

    def test_unrecognized_parameter_preserves_existing_choice(self):
        self.client.get(reverse('admin:index'), {'model_counts': '1'})
        self.assertContains(
            self.client.get(reverse('admin:index'), {'model_counts': 'true'}),
            'Hide record counts',
        )

    def test_staff_counts_only_the_queryset_they_can_view(self):
        self.staff.user_permissions.add(
            Permission.objects.get(
                codename='view_user', content_type__app_label='users'
            )
        )
        self.client.force_login(self.staff)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('admin:index'), {'model_counts': '1'})
        self.assertContains(response, 'Users (2)')
        self.assertNotContains(response, 'Employer invitations')
        counts = [query['sql'] for query in queries if 'COUNT(' in query['sql'].upper()]
        self.assertEqual(len(counts), 1)
        self.assertIn('adviser', counts[0])

    def test_anonymous_request_is_redirected_without_counting(self):
        self.client.logout()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('admin:index'), {'model_counts': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(any('COUNT(' in query['sql'].upper() for query in queries))

    def test_controls_are_translated(self):
        for language, show, hide in (
            (
                'fr',
                'Afficher les nombres d’enregistrements',
                'Masquer les nombres d’enregistrements',
            ),
            (
                'de',
                'Anzahl der Datensätze anzeigen',
                'Anzahl der Datensätze ausblenden',
            ),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = language
                self.assertContains(
                    self.client.get(reverse('admin:index'), {'model_counts': '0'}), show
                )
                self.assertContains(
                    self.client.get(reverse('admin:index'), {'model_counts': '1'}), hide
                )
