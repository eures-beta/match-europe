from django.conf import settings
from django.test import SimpleTestCase, TestCase

from eures_beta.users.models import User

from eures_beta.design_system import (
    RAW_COLOUR,
    TOKEN_USE,
    TOKENS,
    colour_tokens,
    contrast,
    css_files,
    read_css,
    resolve,
    token_declarations,
)

TEXT_TOKENS = (
    '--me-color-text',
    '--me-color-text-muted',
    '--me-color-link',
    '--me-color-link-hover',
    '--me-color-action',
    '--me-color-error',
    '--me-color-border-strong',
    '--me-color-focus',
    '--me-color-text-inverse',
    '--me-color-action-text',
    '--me-color-accent-text',
)


class DesignSystemTokenTests(SimpleTestCase):
    def test_raw_colours_live_only_in_palette_tokens(self):
        for name, value in token_declarations().items():
            if RAW_COLOUR.search(value):
                with self.subTest(token=name):
                    self.assertTrue(
                        name.startswith('--me-palette-'),
                        f'{name} must use a --me-palette-* token, not a raw colour',
                    )

    def test_design_system_files_use_no_raw_colour(self):
        for path in css_files():
            if path == TOKENS:
                continue
            with self.subTest(file=path.name):
                self.assertEqual(RAW_COLOUR.findall(read_css(path)), [])

    def test_every_token_used_is_defined(self):
        defined = set(token_declarations())
        for path in css_files():
            for token in sorted(set(TOKEN_USE.findall(read_css(path)))):
                with self.subTest(file=path.name, token=token):
                    self.assertIn(token, defined)

    def test_rgb_triplets_match_their_colour(self):
        declarations = token_declarations()
        triplets = [name for name in declarations if name.endswith('-rgb')]
        self.assertTrue(triplets)
        for name in triplets:
            with self.subTest(token=name):
                colour = resolve(name.removesuffix('-rgb'), declarations).lstrip('#')
                expected = ', '.join(str(int(colour[i : i + 2], 16)) for i in (0, 2, 4))
                self.assertEqual(resolve(name, declarations), expected)

    def test_text_tokens_meet_wcag_aa(self):
        rows = {row['name']: row for row in colour_tokens('--me-color-')}
        for name in TEXT_TOKENS:
            with self.subTest(token=name):
                self.assertGreaterEqual(rows[name]['contrast'], 4.5)

    def test_headings_use_the_served_gelasio_font(self):
        declarations = token_declarations()
        self.assertTrue(
            declarations['--me-font-family-heading'].startswith("'Gelasio'")
        )
        self.assertIn("url('fonts/Gelasio-wght.ttf')", read_css(TOKENS))
        self.assertTrue((TOKENS.parent / 'fonts' / 'Gelasio-wght.ttf').exists())
        self.assertTrue((TOKENS.parent / 'fonts' / 'Gelasio-OFL.txt').exists())

    def test_text_for_coloured_backgrounds_is_measured_on_that_background(self):
        rows = {token['name']: token for token in colour_tokens('--me-color-')}
        self.assertEqual(rows['--me-color-action-text']['contrast'], 7.5)
        self.assertEqual(rows['--me-color-accent-text']['contrast'], 11.1)
        self.assertEqual(rows['--me-color-text']['background'], '')

    def test_contrast_matches_known_wcag_values(self):
        self.assertAlmostEqual(contrast('#000000'), 21.0)
        self.assertAlmostEqual(contrast('#ffffff'), 1.0)
        self.assertAlmostEqual(contrast('#0e47cb'), 7.55, places=2)


class DesignSystemPageTests(TestCase):
    url = '/design-system/'
    urls = (
        '/design-system/',
        '/design-system/exemple/',
        '/design-system/exemple/mes-offres/',
        '/design-system/exemple/connexion/',
        '/design-system/exemple/candidat/',
        '/design-system/exemple/conseiller/',
    )

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            'equipe@example.invalid', kind='adviser', is_staff=True
        )
        cls.adviser = User.objects.create_user(
            'conseil@example.invalid', kind='adviser'
        )
        cls.employer = User.objects.create_user('rh@example.invalid', kind='employer')

    def test_anonymous_visitors_are_sent_to_login(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{settings.LOGIN_URL}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_pages_are_hidden_from_non_staff_accounts(self):
        for user in (self.adviser, self.employer):
            self.client.force_login(user)
            for url in self.urls:
                with self.subTest(user=user.email, url=url):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_inactive_staff_is_refused(self):
        self.staff.is_active = False
        self.staff.save(update_fields=['is_active'])
        self.client.force_login(self.staff)
        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_unknown_example_screen_is_not_found(self):
        self.client.force_login(self.staff)
        response = self.client.get('/design-system/exemple/admin/')
        self.assertEqual(response.status_code, 404)

    def test_pages_load_the_three_stylesheets_in_order(self):
        self.client.force_login(self.staff)
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response.headers.get('Cache-Control', ''))
                page = response.content.decode()
                positions = [
                    page.index(f'/static/{path}')
                    for path in (
                        'vendor/bootstrap/bootstrap.min.css',
                        'design-system/tokens.css',
                        'design-system/bootstrap-theme.css',
                    )
                ]
                self.assertEqual(positions, sorted(positions))
                self.assertNotIn('employer/site.css', page)

    def test_page_shows_every_colour_token(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        for prefix in ('--me-color-', '--me-palette-'):
            for token in colour_tokens(prefix):
                with self.subTest(token=token['name']):
                    self.assertContains(response, token['name'])
