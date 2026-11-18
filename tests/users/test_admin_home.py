from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AdminHomeTests(TestCase):
    def test_anonymous_and_ordinary_accounts_cannot_open_internal_tools(self):
        url = reverse('admin_home')
        self.assertRedirects(
            self.client.get(url), '/accounts/login/?next=/accounts/admin/'
        )
        for kind in User.Kind.values:
            user = User.objects.create_user(f'{kind}@example.invalid', kind=kind)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get(
                    url, {'is_staff': 'true', 'is_superuser': 'true'}
                ).status_code,
                404,
            )
            self.assertNotContains(self.client.get('/'), 'href="/accounts/admin/')

    def test_staff_and_superusers_have_the_same_hub_in_every_environment(self):
        for kind in User.Kind.values:
            for staff, superuser in ((True, False), (True, True), (False, True)):
                user = User.objects.create_user(
                    f'{kind}-{staff}-{superuser}@example.invalid',
                    kind=kind,
                    is_staff=staff,
                    is_superuser=superuser,
                )
                self.client.force_login(user)
                for environment in ('local', 'preview', 'production'):
                    with (
                        self.subTest(
                            kind=kind,
                            staff=staff,
                            superuser=superuser,
                            environment=environment,
                        ),
                        self.settings(DJANGO_ENVIRONMENT=environment),
                    ):
                        response = self.client.get(
                            reverse('admin_home'), {'lang': 'fr'}
                        )
                        self.assertEqual(response.status_code, 200)
                        self.assertTemplateUsed(response, 'public_base.html')
                        self.assertContains(response, user.email)
                        self.assertContains(response, 'aria-current="page"')
                        self.assertIn('no-store', response['Cache-Control'])
                        self.assertContains(
                            self.client.get('/'), 'href="/accounts/admin/?lang=fr"'
                        )

    def test_hub_lists_cookbook_every_example_and_django_administration(self):
        user = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        other = User.objects.create_user(
            'other-private@example.invalid', kind='employer'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('admin_home'))
        for name in ('design_system', 'design_system_example', 'admin:index'):
            self.assertContains(response, f'href="{reverse(name)}"')
        for screen in ('offre', 'mes-offres', 'connexion', 'candidat', 'conseiller'):
            self.assertContains(
                response,
                f'href="{reverse("design_system_example_screen", args=[screen])}"',
            )
        self.assertNotContains(response, other.email)
        self.assertEqual(self.client.get(reverse('design_system')).status_code, 200)
        # The hub does not grant superuser privileges or access to private models.
        self.assertEqual(
            self.client.get(reverse('admin:employers_joboffer_changelist')).status_code,
            403,
        )
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_account_flags_and_tools_are_translated(self):
        user = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        self.client.force_login(user)
        for language, staff, superuser, yes, no, cookbook in (
            (
                'fr',
                'Membre du staff',
                'Superutilisateur',
                'Oui',
                'Non',
                'Cookbook du design system',
            ),
            ('en', 'Staff member', 'Superuser', 'Yes', 'No', 'Design system cookbook'),
            ('de', 'Teammitglied', 'Superuser', 'Ja', 'Nein', 'Designsystem-Kochbuch'),
        ):
            response = self.client.get(reverse('admin_home'), {'lang': language})
            self.assertContains(response, cookbook)
            self.assertContains(response, f'href="/accounts/admin/?lang={language}"')
            self.assertContains(
                response, f'<dt>{staff}</dt>\n      <dd>{yes}</dd>', html=True
            )
            self.assertContains(
                response, f'<dt>{superuser}</dt>\n      <dd>{no}</dd>', html=True
            )

    def test_hub_is_read_only_and_inactive_accounts_are_rejected(self):
        user = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        self.client.force_login(user)
        self.assertEqual(
            self.client.post(
                reverse('admin_home'), {'is_superuser': 'true'}
            ).status_code,
            405,
        )
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('admin_home')).status_code, 302)
