from html.parser import HTMLParser
from urllib.parse import urljoin

from django.test import SimpleTestCase, override_settings


class LanguageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'lang-link' in attrs.get('class', '').split():
            self.hrefs.append(attrs['href'])


@override_settings(SHARED_DEMO=True)
class LanguageNavigationTests(SimpleTestCase):
    def open_page(self, url):
        # Keep HTTPS while following relative redirects, as a browser does.
        for _ in range(10):
            response = self.client.get(url, secure=True)
            if response.status_code not in (301, 302, 303, 307, 308):
                return response
            url = urljoin(url, response['Location'])
        self.fail('Redirect loop while switching language')

    def assert_language_page(self, url, language):
        response = self.open_page(url)
        self.assertContains(response, f'<html lang="{language}"')
        heading = {
            'fr': 'Recrutez plus facilement',
            'en': 'Make recruitment easier',
            'de': 'Einfacher Personal finden',
        }[language]
        self.assertContains(response, heading)
        return response

    def test_current_home_menu_really_opens_each_language(self):
        home = self.open_page('/')
        self.assertEqual(home.status_code, 200)
        menu = LanguageLinks()
        menu.feed(home.content.decode())
        self.assertEqual(len(menu.hrefs), 3)
        for language, href in zip(('fr', 'en', 'de'), menu.hrefs):
            with self.subTest(language=language):
                url = urljoin(home.wsgi_request.path, href)
                self.assert_language_page(url, language)

    def test_language_switch_from_french_page_already_open_before_deployment(self):
        # These are the relative links in the French page before the URL move.
        # A tab already open during deployment keeps this document and its base URL.
        cached_page_url = '/previews/employer-landing/fr.html'
        for language in ('en', 'de'):
            with self.subTest(language=language):
                self.assert_language_page(
                    urljoin(cached_page_url, f'{language}.html'), language
                )

    def test_existing_french_bookmark_still_has_working_language_links(self):
        page = self.assert_language_page('/previews/employer-landing/fr.html', 'fr')
        menu = LanguageLinks()
        menu.feed(page.content.decode())
        self.assertEqual(len(menu.hrefs), 3)
        for language, href in zip(('fr', 'en', 'de'), menu.hrefs):
            with self.subTest(language=language):
                self.assert_language_page(
                    urljoin(page.wsgi_request.path, href), language
                )

    def test_compatibility_redirect_preserves_query_and_never_exposes_sources(self):
        response = self.client.get(
            '/previews/employer-landing/import-v2-en.html?example=one%20two',
            secure=True,
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response['Location'], '/employer/pages/import-v2-en.html?example=one%20two'
        )
        self.assertEqual(
            self.client.get(
                '/previews/employer-landing/build.cjs', secure=True
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                '/previews/employer-landing/en.html', secure=True
            ).status_code,
            405,
        )
