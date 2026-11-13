"""Keep the HTTP adapter layer out of the business packages."""

import ast

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver


class WebArchitectureTests(SimpleTestCase):
    def test_business_packages_do_not_import_web_adapters(self):
        for package in (
            'users',
            'invitations',
            'employers',
            'candidates',
            'matching',
            'occupations',
            'skills',
        ):
            for path in (settings.APPS_DIR / package).rglob('*.py'):
                if 'migrations' in path.parts:
                    continue
                with self.subTest(path=path.relative_to(settings.BASE_DIR)):
                    tree = ast.parse(path.read_text())
                    modules = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            modules.append(node.module or '')
                        elif isinstance(node, ast.Import):
                            modules.extend(alias.name for alias in node.names)
                    self.assertFalse(
                        any(m.startswith('eures_beta.www') for m in modules)
                    )

    def test_application_routes_are_served_by_the_web_layer(self):
        def visit(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    # Django admin and language switching keep their native views.
                    if (
                        pattern.urlconf_name == 'django.conf.urls.i18n'
                        or pattern.app_name == 'admin'
                    ):
                        continue
                    yield from visit(pattern.url_patterns)
                elif isinstance(pattern, URLPattern):
                    yield pattern

        for pattern in visit(get_resolver().url_patterns):
            if pattern.name in ('health', 'set_language'):
                continue
            callback = pattern.callback
            module = getattr(
                getattr(callback, 'view_class', callback), '__module__', ''
            )
            with self.subTest(route=str(pattern.pattern), name=pattern.name):
                self.assertTrue(
                    module.startswith(('eures_beta.www.', 'django.views.generic.'))
                )
