from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class AdminFilterToggleTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            'filters@example.invalid', kind='adviser'
        )
        self.client.force_login(user)

    def test_toggle_is_translated_and_preserves_active_filter(self):
        for language, show, hide in (
            ('en', 'Show filters', 'Hide filters'),
            ('fr', 'Afficher les filtres', 'Masquer les filtres'),
            ('de', 'Filter anzeigen', 'Filter ausblenden'),
        ):
            with self.subTest(language=language), translation.override(language):
                self.client.cookies['django_language'] = language
                response = self.client.get(
                    reverse('admin:users_user_changelist'), {'kind__exact': 'adviser'}
                )
                self.assertContains(response, 'id="admin-filter-toggle"')
                self.assertContains(response, 'aria-controls="changelist-filter"')
                self.assertContains(response, 'aria-expanded="true"')
                self.assertContains(response, f'data-show-label="{show}"')
                self.assertContains(response, f'data-hide-label="{hide}"')
                self.assertTrue(response.context['cl'].has_active_filters)
                self.assertContains(response, 'admin/filter-toggle.js')
                self.assertContains(response, 'admin/nav-sidebar-default.js')

    def test_lists_without_filters_do_not_offer_an_empty_control(self):
        response = self.client.get(reverse('admin:contenttypes_contenttype_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['cl'].has_filters)
        self.assertNotContains(response, 'id="admin-filter-toggle"')
