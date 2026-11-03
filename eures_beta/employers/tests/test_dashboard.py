from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eures_beta.employers.models import (
    Company,
    JobOffer,
    CompanyMembership,
)

User = get_user_model()


class EmployerDashboardTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        self.other = User.objects.create_user(
            email='other@example.invalid', kind='employer'
        )
        self.company = Company.objects.create(name='Shared fictional workspace')
        self.member = CompanyMembership.objects.create(
            person=self.employer, company=self.company
        )
        self.client.force_login(self.employer)

    def offer(self, title, **fields):
        return JobOffer.objects.create(
            email=self.employer.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={'title': title, 'city': 'Test city'},
            **fields,
        )

    def test_only_active_workspaces_and_own_private_drafts_are_visible(self):
        shared = self.offer('Shared offer', company=self.company, created_by=self.other)
        own = self.offer('My private draft', created_by=self.employer)
        other_company = Company.objects.create(name='Private other workspace')
        self.offer(
            'Other company secret', company=other_company, created_by=self.employer
        )
        self.offer('Other user secret', created_by=self.other)
        self.offer(
            'Anonymous browser secret', session_key=self.client.session.session_key
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(set(response.context['offers']), {shared, own})
        for secret in (
            'Other company secret',
            'Other user secret',
            'Anonymous browser secret',
        ):
            self.assertNotContains(response, secret)
        self.member.active = False
        self.member.save(update_fields=['active'])
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(list(response.context['offers']), [own])

    def test_contact_email_and_query_parameters_do_not_grant_access(self):
        company = Company.objects.create(name='Unrelated workspace')
        self.offer(
            'Secret with matching contact', company=company, created_by=self.other
        )
        response = self.client.get(
            reverse('dashboard'),
            {'lang': 'en', 'company': company.pk, 'user': self.other.pk},
        )
        self.assertNotContains(response, 'Secret with matching contact')
        self.assertContains(response, 'No offers to display yet.')

    def test_html_is_escaped_and_missing_title_and_establishment_are_explained(self):
        offer = self.offer('<script>alert(1)</script>', created_by=self.employer)
        page = self.client.get(reverse('dashboard'), {'lang': 'en'})
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertContains(page, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(page, 'Not attached to an establishment')
        offer.data = {}
        offer.save()
        self.assertContains(
            self.client.get(reverse('dashboard'), {'lang': 'en'}), 'Untitled offer'
        )

    def test_read_only_dashboard_has_no_edit_links_and_rejects_writes(self):
        offer = self.offer('Existing offer', company=self.company)
        before = JobOffer.objects.values().get(pk=offer.pk)
        response = self.client.get(reverse('dashboard'))
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotContains(response, str(offer.pk))
        self.assertNotContains(response, '/employer/offers/')
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(
                getattr(self.client, method)(
                    reverse('dashboard'), {'title': 'Changed'}
                ).status_code,
                405,
            )
        self.assertEqual(before, JobOffer.objects.values().get(pk=offer.pk))

    def test_pagination_preserves_language_and_stable_order(self):
        offers = [self.offer(f'Offer {i}', company=self.company) for i in range(26)]
        page = self.client.get(reverse('dashboard'), {'lang': 'fr'})
        self.assertEqual(list(page.context['offers']), list(reversed(offers[1:])))
        self.assertContains(page, 'lang=fr&amp;offers_page=2')
        second = self.client.get(reverse('dashboard'), {'lang': 'fr', 'offers_page': 2})
        self.assertEqual(list(second.context['offers']), offers[:1])
        self.assertContains(second, 'lang=fr&amp;offers_page=1')
        self.assertEqual(
            self.client.get(
                reverse('dashboard'), {'offers_page': 'invalid'}
            ).status_code,
            200,
        )

    def test_empty_state_in_each_language_and_adviser_dashboard_unchanged(self):
        for language, label in (
            ('fr', 'Aucune offre à afficher pour le moment.'),
            ('en', 'No offers to display yet.'),
            ('de', 'Noch keine Stellenangebote vorhanden.'),
        ):
            self.assertContains(
                self.client.get(reverse('dashboard'), {'lang': language}), label
            )
        adviser = User.objects.create_user(
            email='adviser@example.invalid', kind='adviser'
        )
        self.client.force_login(adviser)
        self.assertTemplateUsed(
            self.client.get(reverse('dashboard')), 'users/adviser_dashboard.html'
        )
