from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse


class PublicNavigationTests(SimpleTestCase):
    def test_legacy_redirects_preserve_language_and_reject_writes(self):
        for suffix, target in (
            ('home', 'home'),
            ('candidate', 'candidate_landing'),
            ('statistics', 'statistics'),
            ('project', 'project'),
            ('journal', 'journal'),
        ):
            legacy = reverse(f'legacy_{suffix}')
            for language in ('fr', 'en', 'de'):
                with self.subTest(page=suffix, language=language):
                    query = f'?lang={language}&source=bookmark'
                    self.assertRedirects(
                        self.client.get(legacy + query, secure=True),
                        reverse(target) + query,
                        status_code=301,
                        fetch_redirect_response=False,
                    )
            self.assertEqual(self.client.post(legacy, secure=True).status_code, 405)

    def test_information_pages_are_translated_and_public(self):
        for route in ('statistics', 'project', 'journal'):
            for language, notice in (
                ('fr', 'Cette page est en construction.'),
                ('en', 'This page is under construction.'),
                ('de', 'Diese Seite befindet sich im Aufbau.'),
            ):
                with (
                    self.subTest(page=route, language=language),
                    override_settings(DEMO_MODE=False),
                ):
                    response = self.client.get(reverse(route), {'lang': language})
                    self.assertTemplateUsed(response, 'under_construction.html')
                    self.assertContains(response, notice)
                    self.assertContains(response, f'<html lang="{language}">')
                    self.assertContains(response, f'href="/?lang={language}"')
                    self.assertEqual(self.client.post(reverse(route)).status_code, 405)

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_menus_use_canonical_routes(self):
        for language in ('fr', 'en', 'de'):
            for path in (
                reverse('home'),
                reverse('candidate_landing'),
                f'/employer/pages/{language}.html',
                f'/employer/pages/import-{language}.html',
                f'/employer/pages/import-v2-{language}.html',
                f'/employer/pages/privacy-{language}.html',
            ):
                with self.subTest(path=path, language=language):
                    response = self.client.get(path, {'lang': language}, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, 'href="/forms/')
                    self.assertNotContains(response, 'href="/previews/')
                    for route in ('statistics', 'project', 'journal'):
                        target = reverse(route) + f'?lang={language}'
                        self.assertContains(response, f'href="{target}"')
                        self.assertEqual(
                            self.client.get(target, secure=True).status_code, 200
                        )

    def test_home_and_dashboard_have_distinct_routes(self):
        self.assertEqual(reverse('dashboard'), '/dashboard/')
        self.assertEqual(resolve(reverse('home')).url_name, 'home')
        self.assertEqual(resolve(reverse('dashboard')).url_name, 'dashboard')

    @override_settings(DEMO_MODE=False)
    def test_legacy_candidate_redirect_does_not_open_the_protected_journey(self):
        response = self.client.get(
            reverse('legacy_candidate'), secure=True, follow=True
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.redirect_chain, [(reverse('candidate_landing'), 301)])
