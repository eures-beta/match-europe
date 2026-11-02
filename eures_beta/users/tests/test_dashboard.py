from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from sesame.utils import get_query_string


class DashboardTests(TestCase):
    def test_dashboard_requires_an_active_account_and_accepts_no_writes(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/accounts/dashboard/')
        user = get_user_model().objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        self.client.force_login(user)
        self.assertEqual(
            self.client.post(
                reverse('dashboard'), {'email': 'new@example.invalid'}
            ).status_code,
            405,
        )
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_both_roles_get_the_same_translated_placeholder_without_other_user_data(
        self,
    ):
        other = get_user_model().objects.create_user(
            email='private-other@example.invalid', kind='adviser'
        )
        for kind in ('adviser', 'employer'):
            user = get_user_model().objects.create_user(
                email=kind + '@example.invalid', kind=kind
            )
            self.client.force_login(user)
            for language, title, notice in (
                ('fr', 'Tableau de bord', 'Votre tableau de bord est en construction.'),
                ('en', 'Dashboard', 'Your dashboard is under construction.'),
                ('de', 'Übersicht', 'Ihre Übersicht befindet sich im Aufbau.'),
            ):
                response = self.client.get(reverse('dashboard'), {'lang': language})
                self.assertContains(response, title)
                if kind == 'employer':
                    self.assertContains(response, notice)
                else:
                    self.assertContains(response, '/accounts/employers/invite/')
                self.assertContains(response, f'href="/accounts/me/?lang={language}"')
                self.assertContains(
                    response, f'href="/accounts/dashboard/?lang={language}"'
                )
                self.assertContains(response, 'aria-current="page"')
                self.assertNotContains(response, other.email)
                self.assertIn('no-store', response['Cache-Control'])
                self.assertTemplateUsed(response, 'public_base.html')

    def test_magic_link_always_lands_on_dashboard_for_each_role_and_staff_status(self):
        for kind, staff in (('employer', False), ('adviser', False), ('adviser', True)):
            user = get_user_model().objects.create_user(
                email=f'{kind}-{staff}@example.invalid', kind=kind, is_staff=staff
            )
            client = Client(enforce_csrf_checks=True)
            response = client.get(
                reverse('magic_confirm') + get_query_string(user),
                secure=True,
                follow=True,
            )
            csrf = client.cookies['csrftoken'].value
            response = client.post(
                reverse('magic_confirm') + '?next=https://attacker.invalid',
                {'csrfmiddlewaretoken': csrf},
                secure=True,
                HTTP_ORIGIN='https://testserver',
                HTTP_REFERER='https://testserver/accounts/confirm/',
            )
            self.assertRedirects(response, reverse('dashboard'))
            self.assertEqual(client.session['_auth_user_id'], str(user.pk))
            self.assertRedirects(
                client.get(reverse('magic_login')), reverse('dashboard')
            )

    def test_anonymous_header_never_displays_private_navigation(self):
        response = self.client.get('/')
        self.assertContains(response, 'href="/accounts/login/')
        for url in (
            '/accounts/dashboard/',
            '/accounts/me/',
            '/admin/',
            '/accounts/logout/',
        ):
            self.assertNotContains(response, f'"{url}')

    def test_switching_account_keeps_the_language_selected_before_confirmation(self):
        previous = get_user_model().objects.create_user(
            email='previous@example.invalid', kind='employer'
        )
        adviser = get_user_model().objects.create_user(
            email='next@example.invalid', kind='adviser'
        )
        self.client.force_login(previous)
        self.client.get(reverse('magic_confirm') + get_query_string(adviser))
        self.client.get(reverse('magic_confirm'), {'lang': 'fr'})
        response = self.client.post(reverse('magic_confirm'), follow=True)
        self.assertEqual(self.client.session['_auth_user_id'], str(adviser.pk))
        self.assertEqual(self.client.session['login_language'], 'fr')
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, '/accounts/employers/invite/')
