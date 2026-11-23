from django.test import TestCase, override_settings
from django.urls import reverse

from eures_beta.users.models import User


class InterfaceLanguageTests(TestCase):
    @override_settings(DEMO_ACCOUNTS_ENABLED=False, DJANGO_ENVIRONMENT='production')
    def test_chosen_language_survives_admin_logout_and_browser_preference(self):
        user = User.objects.create_user(
            'admin@language.example.invalid',
            kind='adviser',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)
        for language in ('fr', 'de', 'en'):
            with self.subTest(language=language):
                self.client.get(reverse('home'), {'lang': language})
                admin = self.client.get(
                    reverse('admin:index'), HTTP_ACCEPT_LANGUAGE='en'
                )
                self.assertEqual(admin['Content-Language'], language)
                self.assertEqual(admin.wsgi_request.LANGUAGE_CODE, language)
                self.client.post(reverse('admin:logout'))
                home = self.client.get(reverse('home'), HTTP_ACCEPT_LANGUAGE='en')
                self.assertEqual(home['Content-Language'], language)
                self.client.force_login(user)

    def test_invalid_query_does_not_replace_the_chosen_language(self):
        self.client.get(reverse('home'), {'lang': 'de'})
        response = self.client.get(reverse('home'), {'lang': 'invalid'})
        self.assertEqual(response.wsgi_request.LANGUAGE_CODE, 'de')
