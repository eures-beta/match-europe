from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.utils import translation


class SharedBrandTests(TestCase):
    def test_public_tabs_share_the_same_brand_in_each_language(self):
        for language in ('fr', 'en', 'de'):
            with translation.override(language):
                brand = render_to_string('includes/public_brand.html')
            for path in ('/candidate/',):
                with self.subTest(language=language, path=path):
                    response = self.client.get(path, {'lang': language}, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'includes/public_brand.html')
                    self.assertInHTML(brand, response.content.decode())
                    self.assertContains(response, 'match-europe-logo.png', count=1)
                    self.assertContains(response, '/static/public-brand.css')

    def test_design_system_pages_share_the_layout_brand_in_each_language(self):
        for language, tagline in (
            ('fr', 'EURES beta'),
            ('en', 'EURES beta - cross-border mobility, matching and follow-up'),
            ('de', 'EURES beta'),
        ):
            for path in (
                f'/?lang={language}',
                f'/statistics/?lang={language}',
                f'/project/?lang={language}',
                f'/journal/?lang={language}',
                f'/employer/?lang={language}',
                f'/employer/import/?lang={language}',
                f'/employer/privacy/?lang={language}',
            ):
                with self.subTest(language=language, path=path):
                    response = self.client.get(path, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'eures_base.html')
                    self.assertContains(response, 'match-europe-logo.png', count=1)
                    self.assertContains(
                        response, f'class="ds-brand" href="/?lang={language}"'
                    )
                    self.assertContains(response, tagline)
                    self.assertNotContains(response, '/static/public-brand.css')

    def test_employer_shell_uses_the_design_system_layout(self):
        for template in ('employer_auth_shell.html',):
            with self.subTest(template=template), translation.override('de'):
                html = render_to_string(template, {'page_language': 'de'})
                self.assertIn('class="ds-brand" href="/?lang=de"', html)
                self.assertIn('/static/design-system/components.css', html)
                self.assertNotIn('/static/public-brand.css', html)

    def test_brand_assets_exist(self):
        for asset in ('public-brand.css', 'employer/assets/match-europe-logo.png'):
            self.assertTrue(finders.find(asset), asset)
