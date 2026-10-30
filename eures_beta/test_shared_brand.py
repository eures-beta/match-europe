from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.utils import translation


@override_settings(DEMO_MODE=True, SHARED_DEMO=True)
class SharedBrandTests(SimpleTestCase):
    def test_public_tabs_share_the_same_brand_in_each_language(self):
        for language in ('fr', 'en', 'de'):
            with translation.override(language):
                brand = render_to_string('includes/public_brand.html')
            for path in (
                '/',
                '/candidate/',
                '/statistics/',
                '/project/',
                '/journal/',
                f'/employer/pages/{language}.html',
                f'/employer/pages/import-{language}.html',
                f'/employer/pages/import-v2-{language}.html',
                f'/employer/pages/privacy-{language}.html',
            ):
                with self.subTest(language=language, path=path):
                    response = self.client.get(path, {'lang': language}, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'includes/public_brand.html')
                    self.assertInHTML(brand, response.content.decode())
                    self.assertContains(response, 'match-europe-logo.png', count=1)
                    self.assertContains(response, '/static/public-brand.css')

    def test_role_and_employer_shells_use_the_shared_brand(self):
        for template in ('base.html', 'employer_auth_shell.html'):
            with self.subTest(template=template), translation.override('de'):
                html = render_to_string(template, {'page_language': 'de'})
                self.assertInHTML(render_to_string('includes/public_brand.html'), html)
                self.assertIn('href="/?lang=de"', html)

    def test_brand_assets_exist(self):
        for asset in ('public-brand.css', 'employer/assets/match-europe-logo.png'):
            self.assertTrue(finders.find(asset), asset)
