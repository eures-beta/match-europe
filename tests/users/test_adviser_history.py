from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates.models import CandidateProfile
from eures_beta.invitations.models import Invitation
from eures_beta.employers.models import JobOffer
from eures_beta.users.models import User
from eures_beta.users.permissions import synchronize_permissions


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
            sender_adviser=cls.adviser,
            email_sent_at=timezone.now(),
        )
        Invitation.objects.create(
            email='unsent@example.invalid', sender_adviser=cls.adviser
        )

    def history(self, **params):
        return self.client.get(reverse('dashboard'), {'tab': 'history', **params})

    def test_adviser_without_extra_permissions_reads_history(self):
        self.adviser.groups.clear()
        self.adviser.user_permissions.clear()
        self.client.force_login(self.adviser)
        response = self.history(view='invitations')
        self.assertContains(response, '/static/adviser/history.css')
        self.assertNotContains(response, '<style')
        self.assertLess(
            response.content.index(b'/static/invitations/invitations.css'),
            response.content.index(b'/static/adviser/history.css'),
        )
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

    def make_offer(self, **values):
        employer, _ = User.objects.get_or_create(
            email='recruiter@example.invalid', defaults={'kind': 'employer'}
        )
        defaults = dict(
            employer=employer,
            session_key='private-session-must-stay-hidden',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={
                'title': 'Technicien test',
                'companyName': 'Entreprise fictive',
                'city': 'Metz',
                'description': '<script>unsafe()</script>',
                'contractType': 'PERMANENT_CONTRACT',
                'clarifications': {'salary': '2500 EUR'},
                'requirements': {
                    'workConditions': ['night'],
                    'arrivalAids': ['housing'],
                },
                'questions': [{'question': 'Disponible le lundi ?', 'mandatory': True}],
            },
            contact={
                'name': 'Contact fictif',
                'email': 'contact@example.invalid',
                'phone': '0000000000',
            },
            structured_requirements={
                'country': 'FR',
                'languages': [{'code': 'de', 'level': 'B1'}],
                'schedule': ['monday:morning'],
                'schedule_mandatory': True,
                'salary': {
                    'maximum': 3000,
                    'currency': 'EUR',
                    'period': 'month',
                    'basis': 'gross',
                },
            },
            source_url='https://example.invalid/offer?token=hidden-token',
            sandbox_response={'token': 'hidden-external-token'},
        )
        defaults.update(values)
        return JobOffer.objects.create(**defaults)

    def test_employer_history_includes_all_recorded_offers_without_matching_changes(
        self,
    ):
        offer = self.make_offer()
        validated = self.make_offer(validated_at=timezone.now(), source_kind='pdf')
        legacy = self.make_offer(
            employer=None,
            data={},
        )
        self.client.force_login(self.adviser)
        response = self.history(view='employers', lang='fr')
        self.assertEqual(
            response.context['page'].paginator.count, JobOffer.objects.count()
        )
        self.assertContains(response, 'Offres employeur')
        self.assertContains(response, 'En préparation')
        self.assertContains(response, 'Validée')
        from eures_beta.matching import access

        self.assertEqual(list(access.offers()), [validated])
        with self.settings(MATCHING_ENABLED=False):
            self.assertContains(self.history(view='employers'), 'Technicien test')
        for query in (
            'Metz',
            'Entreprise fictive',
            'recruiter@',
        ):
            self.assertGreater(
                self.history(view='employers', q=query).context['page'].paginator.count,
                0,
            )
        self.assertEqual(
            self.history(view='employers', q='legacy@').context['page'].paginator.count,
            0,
        )
        response = self.history(view='employers', entry=legacy.pk)
        self.assertContains(response, str(legacy.pk))
        self.assertEqual(offer.revision, 1)

    def test_offer_details_are_readable_translated_and_escape_untrusted_content(self):
        offer = self.make_offer()
        self.client.force_login(self.adviser)
        for lang, heading, contract in [
            ('fr', 'Offres employeur', 'CDI'),
            ('en', 'Employer job offers', 'Permanent contract'),
            ('de', 'Stellenangebote der Arbeitgeber', 'Unbefristeter Vertrag'),
        ]:
            with self.subTest(lang=lang):
                response = self.history(view='employers', entry=offer.pk, lang=lang)
                self.assertContains(response, heading)
                self.assertContains(response, contract)
                for value in (
                    '2500 EUR',
                    'Contact fictif',
                    offer.employer.email,
                    'DE B1',
                    '3000',
                    'Disponible le lundi ?',
                    str(offer.pk),
                ):
                    self.assertContains(response, value)
                for secret in (
                    'private-session-must-stay-hidden',
                    'hidden-token',
                    'hidden-external-token',
                    '<script>unsafe()',
                ):
                    self.assertNotContains(response, secret)
                self.assertContains(response, '&lt;script&gt;')
                self.assertIn('no-store', response['Cache-Control'])
        self.assertIsNone(
            self.history(view='employers', entry=offer.pk, q='absent').context[
                'selected_entry'
            ]
        )
        self.assertIsNone(
            self.history(view='employers', entry='not-a-uuid').context['selected_entry']
        )

    def test_employer_data_permissions_pagination_and_read_only(self):
        offer = self.make_offer()
        employer = offer.employer
        for user in (employer, self.candidate):
            self.client.force_login(user)
            self.assertEqual(
                self.history(view='employers', entry=offer.pk).status_code, 403
            )
        self.client.logout()
        self.assertEqual(
            self.history(view='employers', entry=offer.pk).status_code, 302
        )
        self.client.force_login(self.adviser)
        self.assertEqual(
            self.client.post(
                reverse('dashboard'), {'tab': 'history', 'view': 'employers'}
            ).status_code,
            405,
        )
        for index in range(20):
            self.make_offer(data={'title': f'Offre {index}'})
        response = self.history(view='employers', entry=offer.pk)
        self.assertEqual(len(response.context['page']), 20)
        self.assertIsNone(response.context['selected_entry'])
        self.assertIsNotNone(
            self.history(view='employers', page=2, entry=offer.pk).context[
                'selected_entry'
            ]
        )
        self.adviser.is_active = False
        self.adviser.save(update_fields=['is_active'])
        self.assertEqual(
            self.history(view='employers', entry=offer.pk).status_code, 302
        )
