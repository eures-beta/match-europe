from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile
from eures_beta.users.models import Invitation, User
from eures_beta.users.permissions import synchronize_permissions


@override_settings(MATCHING_ENABLED=True)
class AdviserHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        synchronize_permissions()
        cls.adviser = User.objects.create_user(
            'adviser@example.invalid', kind='adviser'
        )
        cls.candidate = User.objects.create_user(
            'candidate@example.invalid', kind='candidate'
        )
        cls.profile = CandidateProfile.objects.create(
            user=cls.candidate,
            display_name='Camille Test',
            email_verified_at=timezone.now(),
            desired_occupations='Métier fictif',
            desired_countries=['FR'],
            mobility='move',
            availability='now',
            contract_types=['permanent'],
            working_time=['full'],
            schedule_preference='varied',
            working_conditions=['discuss'],
            salary_preference='discuss',
            language_skills={
                'status': 'specified',
                'languages': [{'code': 'de', 'level': 'B1'}],
            },
        )
        Invitation.objects.create(
            email='sent@example.invalid',
            sender=cls.adviser,
            email_sent_at=timezone.now(),
        )
        Invitation.objects.create(email='unsent@example.invalid', sender=cls.adviser)

    def history(self, **params):
        return self.client.get(reverse('dashboard'), {'tab': 'history', **params})

    def test_adviser_without_extra_permissions_reads_history(self):
        self.adviser.groups.clear()
        self.adviser.user_permissions.clear()
        self.client.force_login(self.adviser)
        response = self.history(view='invitations')
        self.assertContains(response, 'sent@example.invalid')
        self.assertNotContains(response, 'unsent@example.invalid')
        self.assertEqual(self.history(view='matchings').status_code, 200)
        self.assertNotContains(
            self.history(view='invitations', q='no result'), 'sent@example.invalid'
        )

    def test_adviser_role_opens_all_sections(self):
        self.adviser.groups.clear()
        self.adviser.user_permissions.clear()
        self.client.force_login(self.adviser)
        for section in ('candidates', 'employers', 'matchings', 'invitations'):
            with self.subTest(section=section):
                self.assertEqual(self.history(view=section).status_code, 200)

        response = self.history(view='candidates', q='Camille', entry=self.profile.pk)
        self.assertContains(response, 'de — B1')
        self.assertNotContains(
            self.history(view='candidates', q='Autre', entry=self.profile.pk),
            'de — B1',
        )

    def test_candidate_cannot_read_history(self):
        self.client.force_login(self.candidate)
        self.assertEqual(self.history(view='invitations').status_code, 403)
