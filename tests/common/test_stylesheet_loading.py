from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import reverse


class StylesheetLoadingTests(SimpleTestCase):
    def test_public_layouts_load_existing_css_in_cascade_order(self):
        for route, layout in (
            ('home', 'public/layout.css'),
            ('candidate_landing', 'public/layout.css'),
        ):
            with self.subTest(route=route):
                page = self.client.get(reverse(route))
                self.assertEqual(page.status_code, 200)
                self.assertNotContains(page, '<style')
                css = [
                    'employer/site.css',
                    layout,
                    'public/header-actions.css',
                    'public-brand.css',
                ]
                positions = [
                    page.content.index(('/static/' + name).encode()) for name in css
                ]
                self.assertEqual(positions, sorted(positions))
                for name in css:
                    self.assertIsNotNone(finders.find(name), name)

    def test_design_system_pages_load_its_css_in_cascade_order(self):
        for route in ('employer_landing',):
            with self.subTest(route=route):
                page = self.client.get(reverse(route))
                self.assertEqual(page.status_code, 200)
                self.assertNotContains(page, '<style')
                self.assertNotContains(page, '/static/employer/site.css')
                css = [
                    'vendor/bootstrap/bootstrap.min.css',
                    'design-system/tokens.css',
                    'design-system/bootstrap-theme.css',
                    'design-system/components.css',
                ]
                positions = [
                    page.content.index(('/static/' + name).encode()) for name in css
                ]
                self.assertEqual(positions, sorted(positions))
                for name in css:
                    self.assertIsNotNone(finders.find(name), name)

    def test_private_stylesheets_are_discoverable_by_collectstatic(self):
        for name in (
            'employer/layout.css',
            'employer/import-layout.css',
            'employer/auth-layout.css',
            'employer/workspace.css',
            'adviser/history.css',
        ):
            with self.subTest(name=name):
                self.assertIsNotNone(finders.find(name))
