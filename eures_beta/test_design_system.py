from django.test import SimpleTestCase, TestCase, override_settings

from eures_beta.design_system import (
    DIRECTIONS,
    RAW_COLOUR,
    THEMES_DIR,
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

    def test_directions_only_override_existing_tokens(self):
        base = set(token_declarations())
        for direction in DIRECTIONS[1:]:
            self.assertTrue((THEMES_DIR / f'{direction}.css').exists())
            overrides = set(token_declarations(direction)) - base
            with self.subTest(direction=direction):
                self.assertEqual(overrides, set())

    def test_rgb_triplets_match_their_colour(self):
        for direction in DIRECTIONS:
            declarations = token_declarations(direction)
            triplets = [name for name in declarations if name.endswith('-rgb')]
            self.assertTrue(triplets)
            for name in triplets:
                with self.subTest(direction=direction, token=name):
                    colour = resolve(name.removesuffix('-rgb'), declarations)
                    colour = colour.lstrip('#')
                    expected = ', '.join(
                        str(int(colour[i : i + 2], 16)) for i in (0, 2, 4)
                    )
                    self.assertEqual(resolve(name, declarations), expected)

    def test_text_tokens_meet_wcag_aa_in_every_direction(self):
        for direction in DIRECTIONS:
            rows = {row['name']: row for row in colour_tokens('--me-color-', direction)}
            for name in TEXT_TOKENS:
                with self.subTest(direction=direction, token=name):
                    self.assertGreaterEqual(rows[name]['contrast'], 4.5)

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

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_unknown_example_screen_is_not_found(self):
        response = self.client.get('/design-system/exemple/admin/', secure=True)
        self.assertEqual(response.status_code, 404)

    @override_settings(DEMO_MODE=False, SHARED_DEMO=False)
    def test_pages_are_hidden_outside_demo_mode(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                self.assertEqual(response.status_code, 404)

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_pages_require_https_on_shared_demo(self):
        for url in self.urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_pages_load_the_three_stylesheets_in_order(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                self.assertEqual(response.status_code, 200)
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

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_example_previews_only_known_heading_fonts(self):
        url = '/design-system/exemple/'
        response = self.client.get(url, {'titres': 'gelasio'}, secure=True)
        self.assertContains(response, 'ds-heading-gelasio')
        response = self.client.get(url, {'titres': '"><script>'}, secure=True)
        self.assertContains(response, 'ds-heading-direction')
        self.assertNotContains(response, '<script>')

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_example_applies_only_known_directions(self):
        url = '/design-system/exemple/conseiller/'
        response = self.client.get(url, {'direction': 'continuite'}, secure=True)
        self.assertContains(response, 'class="ds-direction-continuite"')
        self.assertContains(response, 'design-system/themes/continuite.css')
        response = self.client.get(url, {'direction': 'autre'}, secure=True)
        self.assertContains(response, 'class="ds-direction-eures"')

    @override_settings(DEMO_MODE=True, SHARED_DEMO=True)
    def test_page_shows_every_colour_token(self):
        response = self.client.get(self.url, secure=True)
        for prefix in ('--me-color-', '--me-palette-'):
            for token in colour_tokens(prefix):
                with self.subTest(token=token['name']):
                    self.assertContains(response, token['name'])
