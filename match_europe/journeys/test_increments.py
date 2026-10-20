from django.test import TestCase, Client
from django.core.management import call_command
from django.conf import settings
class IncrementTests(TestCase):
    def test_configuration_and_schema(self):
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        from journeys.models import Profile
        self.assertEqual(Profile.objects.count(), 0)
    def test_confirmation_is_single_use(self):
        from django.contrib.auth.models import User
        from journeys.models import Profile
        from journeys.services import issue_token, consume_token
        user=User.objects.create_user('stage@example.invalid')
        Profile.objects.create(user=user,role='employer')
        token=issue_token(user)
        self.assertEqual(consume_token(token).pk,user.pk)
        self.assertIsNone(consume_token(token))
    def test_models_match_migration_state(self):
        call_command('makemigrations',check=True,dry_run=True,verbosity=0)
    def test_seed_and_role_access(self):
        from django.contrib.auth.models import User
        call_command('seed_demo', verbosity=0)
        for role in ['employer','candidate','adviser','admin']:
            client=Client();user=User.objects.get(profile__role=role)
            self.assertEqual(client.post('/demo/%s/' % user.pk).status_code,302)
            self.assertEqual(client.get('/').status_code,200)
        self.assertEqual(Client().get('/').status_code,302)
        self.assertEqual(Client().get('/access/').status_code,200)
    def test_language_selector(self):
        self.assertEqual(self.client.post('/i18n/setlang/', {'language':'en','next':'/access/'}).status_code,302)
        self.assertIn('en',dict(settings.LANGUAGES))
    def test_employer_offer_access(self):
        from django.contrib.auth.models import User
        from journeys.models import Offer
        call_command('seed_demo', verbosity=0)
        user=User.objects.get(profile__role='employer');self.client.force_login(user)
        offer=Offer.objects.get()
        self.assertEqual(self.client.get('/offers/%s/' % offer.pk).status_code,200)
        self.client.logout();self.assertEqual(self.client.get('/offers/%s/' % offer.pk).status_code,302)


from django.test import SimpleTestCase
class PreviewResourceTests(SimpleTestCase):
    def test_preview_local_resources(self):
        import os,re
        from unittest.mock import patch
        from urllib.parse import urljoin
        pages=['en.html','fr.html','de.html','import-en.html','privacy-en.html']
        with patch.dict(os.environ,{'ME_EMPLOYER_LOCAL_API':'1'}):
            for page in pages:
                url='/previews/employer-landing/'+page
                response=self.client.get(url)
                self.assertEqual(response.status_code,200,url)
                html=response.content.decode()
                for attribute,reference in re.findall(r'(src|href)="([^"]+)',html):
                    if reference.startswith(('https:','http:','data:','#')):continue
                    if attribute=='href' and not reference.endswith('.css'):continue
                    resource=self.client.get(urljoin(url,reference))
                    self.assertEqual(resource.status_code,200,reference)
                    resource.close()
