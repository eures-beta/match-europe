"""Model names stay English; admin controls and public metadata stay localized."""

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.test import TestCase
from django.urls import reverse
from django.utils import translation
from django.utils.text import capfirst

from eures_beta.users.models import User
from eures_beta.users.admin_labels import EnglishModelOptions
from eures_beta.planning.models import StaffDailyAvailability


class AdminModelNameTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            'admin-labels@example.invalid', kind='adviser'
        )

    def localized_get(self, path, language):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
        return self.client.get(path)

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_registered_model_uses_english_names_in_localized_index(self):
        for language in ('fr', 'de', 'en'):
            response = self.localized_get(reverse('admin:index'), language)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Language'], language)
            with translation.override('en'):
                expected = {
                    model._meta.object_name: capfirst(
                        str(model._meta.verbose_name_plural)
                    )
                    for model in admin.site._registry
                }
            for app in response.context['app_list']:
                for entry in app['models']:
                    self.assertEqual(entry['name'], expected[entry['object_name']])
            if language == 'fr':
                self.assertIn('Afficher', response.content.decode())
                self.assertContains(response, 'Staff daily availabilities')
                self.assertContains(response, 'Log entries')
                self.assertNotContains(response, 'Entrées d’historique')

    def test_changelist_and_detail_keep_english_model_names(self):
        expected = EnglishModelOptions(User._meta)
        for language in ('fr', 'de'):
            response = self.localized_get(
                reverse('admin:users_user_changelist'), language
            )
            self.assertEqual(
                response.context['opts'].verbose_name_plural,
                expected.verbose_name_plural,
            )
            self.assertIn(expected.verbose_name, response.context['cl'].title)
            self.assertEqual(
                response.context['cl'].opts.verbose_name, expected.verbose_name
            )
            detail = self.localized_get(
                reverse('admin:users_user_change', args=[self.user.pk]), language
            )
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.context['opts'].verbose_name, expected.verbose_name)
            self.assertIn(expected.verbose_name, detail.context['title'])

    def test_shared_metadata_and_other_languages_are_never_mutated(self):
        original = LogEntry._meta
        with translation.override('fr'):
            french = str(original.verbose_name)
            options = EnglishModelOptions(original)
            self.assertEqual(str(original.verbose_name), french)
            self.assertNotEqual(options.verbose_name, french)
            self.client.get(reverse('admin:index'), {'lang': 'en'})
        with translation.override('fr'):
            self.assertIs(LogEntry._meta, original)
            self.assertEqual(str(LogEntry._meta.verbose_name), french)
        self.assertEqual(
            EnglishModelOptions(StaffDailyAvailability._meta).verbose_name_plural,
            'staff daily availabilities',
        )
