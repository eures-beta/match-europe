import os
from unittest.mock import patch

from django.test import TestCase, override_settings


@override_settings(DEMO_MODE=True, SHARED_DEMO=False)
class EmployerAuthTranslationTests(TestCase):
    @patch.dict(os.environ, {'ME_EMPLOYER_EMAIL_LOCAL': '1'})
    def test_access_shell_is_shared_and_navigation_uses_the_selected_language(self):
        for language, label in (
            ('en', 'Sign in'),
            ('fr', 'Me connecter'),
            ('de', 'Anmelden'),
        ):
            with self.subTest(language=language):
                self.client.cookies['django_language'] = (
                    'fr' if language == 'en' else 'en'
                )
                response = self.client.get(f'/employer/access/?lang={language}')
                self.assertTemplateUsed(response, 'employer_auth_shell.html')
                self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(response, label)
                self.assertContains(response, f'href="/employer/pages/{language}.html"')
                self.assertContains(
                    response, f'href="/employer/pages/privacy-{language}.html"'
                )
                self.assertContains(
                    response,
                    f'class="lang-link is-active" href="/employer/access/?lang={language}"',
                )
