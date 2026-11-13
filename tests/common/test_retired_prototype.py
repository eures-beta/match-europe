from django.contrib.auth import get_user_model
from django.core.management import get_commands
from django.test import TestCase, override_settings
from django.urls import resolve, Resolver404


class RetiredPrototypeTests(TestCase):
    def test_old_routes_are_absent_even_with_an_authenticated_or_draft_session(self):
        user = get_user_model().objects.create_user(
            kind='adviser', email='retired-test@example.invalid'
        )
        self.client.force_login(user)
        session = self.client.session
        session['draft_user'] = user.pk
        session.save()
        for path in (
            '/access/',
            '/demo/1/',
            '/confirm/token/',
            '/logout/',
            '/dashboard/',
            '/profile/',
            '/upload/',
            '/offers/1/',
            '/matches/1/',
            '/conversations/1/',
            '/conversations/1/feed/',
            '/notifications/read/',
            '/documents/1/',
            '/imported-offers/00000000-0000-0000-0000-000000000001/',
        ):
            with self.subTest(path=path):
                with self.assertRaises(Resolver404):
                    resolve(path)
                self.assertEqual(self.client.get(path, secure=True).status_code, 404)
                self.assertEqual(self.client.post(path, secure=True).status_code, 404)

    def test_current_public_pages_keep_all_three_languages(self):
        for language in ('fr', 'en', 'de'):
            for path in (
                '/',
                '/candidate/',
                '/statistics/',
                '/project/',
                '/journal/',
                f'/employer/?lang={language}',
                f'/employer/import/?lang={language}',
            ):
                with self.subTest(path=path, language=language):
                    response = self.client.get(path, {'lang': language}, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, 'Try the four journeys')
        self.assertFalse(get_user_model().objects.exists())
        self.assertNotIn('seed_demo', get_commands())
