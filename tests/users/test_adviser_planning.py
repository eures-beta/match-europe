from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from eures_beta.users.models import AdviserAvailability, User


class AdviserPlanningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adviser = User.objects.create_user(
            'planner@example.invalid', kind='adviser', first_name='Camille Test'
        )
        cls.colleague = User.objects.create_user(
            'colleague@example.invalid', kind='adviser', first_name='Sam Test'
        )
        cls.inactive = User.objects.create_user(
            'inactive@example.invalid',
            kind='adviser',
            is_active=False,
            first_name='Inactive Test',
        )
        cls.candidate = User.objects.create_user(
            'candidate@example.invalid', kind='candidate', first_name='Candidate Test'
        )
        cls.employer = User.objects.create_user(
            'employer@example.invalid', kind='employer'
        )

    def setUp(self):
        self.day = date(2026, 11, 23)
        self.url = reverse('adviser_planning', query={'lang': 'en', 'week': self.day})

    def test_only_active_advisers_are_listed_and_own_row_is_editable(self):
        AdviserAvailability.objects.create(
            adviser=self.colleague, day=self.day, present=False
        )
        self.client.force_login(self.adviser)
        response = self.client.get(self.url)
        self.assertContains(response, 'Camille Test')
        self.assertContains(response, 'Sam Test')
        self.assertNotContains(response, 'Inactive Test')
        self.assertNotContains(response, 'Candidate Test')
        self.assertNotContains(response, self.colleague.email)
        self.assertContains(response, 'name="status"', count=7)
        self.assertContains(response, 'planning-status-absent', count=1)
        self.assertEqual(response.context['previous_week'], date(2026, 11, 16))
        self.assertEqual(response.context['next_week'], date(2026, 11, 30))

    def test_save_change_and_retry_only_touch_signed_in_adviser(self):
        other = AdviserAvailability.objects.create(
            adviser=self.colleague, day=self.day, present=False
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.adviser)
        client.get(self.url)
        data = {
            'day': self.day.isoformat(),
            'status': 'present',
            'adviser': self.colleague.pk,
        }
        self.assertEqual(client.post(self.url, data).status_code, 403)
        data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        for status in ('present', 'present', 'absent'):
            response = client.post(self.url, {**data, 'status': status})
            self.assertRedirects(response, self.url)
            own = AdviserAvailability.objects.get(adviser=self.adviser, day=self.day)
            self.assertEqual(own.present, status == 'present')
        other.refresh_from_db()
        self.assertFalse(other.present)

    def test_guest_and_other_roles_cannot_read_or_save(self):
        for user in (None, self.candidate, self.employer, self.inactive):
            with self.subTest(user=user):
                client = Client()
                if user:
                    client.force_login(user)
                self.assertEqual(client.get(self.url).status_code, 403)
                response = client.post(
                    self.url, {'day': self.day.isoformat(), 'status': 'present'}
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(AdviserAvailability.objects.exists())

    def test_invalid_week_date_and_status_are_rejected(self):
        self.client.force_login(self.adviser)
        self.assertEqual(
            self.client.get(
                reverse('adviser_planning') + '?week=2026-02-31'
            ).status_code,
            400,
        )
        for data in (
            {'day': '2026-11-30', 'status': 'present'},
            {'day': '2026-11-23', 'status': 'unexpected'},
        ):
            self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.assertFalse(AdviserAvailability.objects.exists())

    def test_schedule_is_translated(self):
        self.client.force_login(self.adviser)
        for language, title in (
            ('en', 'Agent schedule'),
            ('fr', 'Planning agent'),
            ('de', 'Dienstplan'),
        ):
            response = self.client.get(reverse('adviser_planning'), {'lang': language})
            self.assertContains(response, title)
