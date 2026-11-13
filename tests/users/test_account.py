from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from eures_beta.www.invitations.adviser import render_message


class AccountPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='owner@example.invalid',
            kind='employer',
            first_name='Fictional',
            last_name='Example',
        )
        self.other = get_user_model().objects.create_user(
            email='other@example.invalid', kind='adviser'
        )

    def test_anonymous_users_cannot_read_account_information(self):
        response = self.client.get(reverse('account'))
        self.assertRedirects(response, '/accounts/login/?next=/accounts/me/')
        self.assertNotContains(self.client.get('/'), 'href="/accounts/me/')

    def test_each_role_sees_only_its_own_account(self):
        for user in (self.user, self.other):
            self.client.force_login(user)
            response = self.client.get(
                reverse('account'),
                {'user': self.other.pk if user == self.user else self.user.pk},
            )
            self.assertTemplateUsed(response, 'public_base.html')
            self.assertContains(response, user.email)
            self.assertNotContains(
                response, self.other.email if user == self.user else self.user.email
            )
            self.assertContains(response, user.get_kind_display())
            self.assertNotContains(response, 'type="password"')
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(
                self.client.post(
                    reverse('account'), {'email': 'changed@example.invalid'}
                ).status_code,
                405 if user == self.user else 302,
            )
            user.refresh_from_db()
            self.assertNotEqual(user.email, 'changed@example.invalid')

    def test_adviser_updates_own_employer_email_signature(self):
        self.client.force_login(self.other)
        url = reverse('account', query={'lang': 'fr'})
        page = self.client.get(url)
        for label in ('Prénom', 'Nom', 'Structure', 'Ces informations seront reprises'):
            self.assertContains(page, label)
        response = self.client.post(
            url,
            {
                'first_name': 'Lou',
                'last_name': 'Martin',
                'organization_name': 'Structure fictive',
                'user': self.user.pk,
                'email': 'changed@example.invalid',
            },
            follow=True,
        )
        self.assertContains(response, 'Votre signature a été enregistrée.')
        self.other.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.other.email, 'other@example.invalid')
        self.assertEqual(self.user.get_full_name(), 'Fictional Example')
        _, body, html = render_message(
            'employer', {'first_name': '', 'last_name': ''}, adviser=self.other
        )
        for version in (body, html):
            self.assertIn('Lou Martin', version)
            self.assertIn('Structure fictive', version)

    def test_adviser_signature_update_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        self.assertEqual(
            client.post(reverse('account'), {'first_name': 'Lou'}).status_code, 403
        )

    def test_account_content_and_navigation_are_translated(self):
        self.client.force_login(self.user)
        for language, title, kind, created, logout in (
            ('fr', 'Mon compte', 'Employeur', 'Compte créé le', 'Me déconnecter'),
            ('en', 'My account', 'Employer', 'Account created on', 'Sign out'),
            ('de', 'Mein Konto', 'Arbeitgeber', 'Konto erstellt am', 'Abmelden'),
        ):
            response = self.client.get(reverse('account'), {'lang': language})
            for text in (
                title,
                kind,
                created,
                logout,
                self.user.email,
                'Fictional Example',
            ):
                self.assertContains(response, text)
            self.assertContains(response, 'aria-current="page"')

    def test_navigation_and_staff_admin_link_are_consistent_on_public_pages(self):
        for user, staff in ((self.user, False), (self.other, True)):
            if staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            self.client.force_login(user)
            for path in (
                '/',
                '/candidate/',
                '/project/',
                '/journal/',
                '/statistics/',
                '/accounts/dashboard/',
                '/employer/pages/fr.html',
                '/employer/pages/import-fr.html',
                '/employer/pages/privacy-fr.html',
                reverse('account'),
            ):
                with self.subTest(path=path, staff=staff):
                    response = self.client.get(path, secure=True)
                    self.assertContains(response, 'href="/accounts/me/?lang=fr"')
                    self.assertContains(response, 'href="/accounts/dashboard/?lang=fr"')
                    self.assertContains(response, 'Me déconnecter')
                    self.assertContains(response, 'action="/accounts/logout/"')
                    self.assertNotContains(response, 'href="/accounts/login/')
                    if staff:
                        self.assertContains(response, 'href="/admin/"')
                    else:
                        self.assertNotContains(response, 'href="/admin/"')
            if not staff:
                self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_logout_remains_post_and_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.get('/accounts/logout/').status_code, 405)
        self.assertEqual(client.post('/accounts/logout/').status_code, 403)

    def test_inactive_account_cannot_read_profile(self):
        self.client.force_login(self.user)
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)
