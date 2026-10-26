import hashlib
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client
from django.utils import timezone
from ..models import EmployerEmailLink


@patch.dict('os.environ', {'ME_EMPLOYER_EMAIL_LOCAL': '1'})
class EmployerLoginTests(TestCase):
    def issue(self, email='fiction@example.invalid'):
        self.client.post('/employer/access/', {'email': email})
        return self.client.session['employer_test_message']['link']

    def test_link_single_use_and_logout(self):
        url = self.issue()
        raw = url.rstrip('/').split('/')[-1]
        self.assertEqual(
            EmployerEmailLink.objects.get().digest,
            hashlib.sha256(raw.encode()).hexdigest(),
        )
        self.client.get(url)  # Email scanners must not consume the link.
        self.assertFalse(EmployerEmailLink.objects.get().used)
        other = Client()
        self.assertRedirects(other.post(url), '/employer/connected/')
        self.assertEqual(
            other.session['employer_verified_email'], 'fiction@example.invalid'
        )
        self.assertNotIn('_auth_user_id', other.session)
        self.client.post(url)
        self.assertNotIn('employer_verified_email', self.client.session)
        other.post('/employer/logout/')
        self.assertNotIn('employer_verified_email', other.session)

    def test_email_button_opens_space_directly(self):
        url = self.issue('direct@example.invalid')
        response = self.client.get('/employer/test-inbox/?lang=fr')
        self.assertContains(response, 'Vérifier mon adresse email')
        self.assertContains(response, 'method="post" action="' + url + '"')
        self.assertRedirects(self.client.post(url), '/employer/connected/')
        self.assertContains(
            self.client.get('/employer/connected/'), 'Mon espace employeur'
        )

    def test_sent_page_separates_test_inbox(self):
        response = self.client.post(
            '/employer/access/', {'email': 'screen@example.invalid'}
        )
        self.assertRedirects(response, '/employer/email-sent/')
        response = self.client.get('/employer/email-sent/?lang=fr')
        self.assertContains(response, 'Consultez votre email')
        self.assertContains(response, 'Pour le test : voir l’email simulé')
        self.assertNotContains(response, '/employer/confirm/')

    def test_expired_and_invalid_links(self):
        url = self.issue()
        EmployerEmailLink.objects.update(expires=timezone.now() - timedelta(seconds=1))
        self.client.post(url)
        self.client.post('/employer/confirm/invalid/')
        self.assertNotIn('employer_verified_email', self.client.session)

    def test_inbox_isolation_and_throttle(self):
        self.issue()
        self.assertNotContains(
            Client().get('/employer/test-inbox/'), 'fiction@example.invalid'
        )
        self.client.post('/employer/access/', {'email': 'other@example.invalid'})
        self.assertEqual(EmployerEmailLink.objects.count(), 1)

    def test_guards(self):
        self.assertEqual(
            self.client.get('/employer/access/', REMOTE_ADDR='10.0.0.1').status_code,
            404,
        )
        with patch.dict('os.environ', {'ME_EMPLOYER_EMAIL_LOCAL': '0'}):
            self.assertEqual(self.client.get('/employer/access/').status_code, 404)
        with self.settings(DEMO_MODE=False):
            self.assertEqual(self.client.get('/employer/access/').status_code, 404)
        self.assertRedirects(
            self.client.get('/employer/connected/'), '/employer/access/'
        )
        csrf = Client(enforce_csrf_checks=True)
        self.assertEqual(
            csrf.post(
                '/employer/access/', {'email': 'fiction@example.invalid'}
            ).status_code,
            403,
        )

    def test_languages(self):
        for language, title in [
            ('fr', 'Accéder à votre espace employeur'),
            ('en', 'Access your employer space'),
            ('de', 'Zugang zu Ihrem Arbeitgeberbereich'),
        ]:
            self.assertContains(
                self.client.get(
                    '/employer/access/?lang=' + language, HTTP_ACCEPT_LANGUAGE=language
                ),
                title,
            )

    def test_new_link_invalidates_previous_and_rotates_session(self):
        old = self.issue()
        session = self.client.session
        session['employer_email_sent_at'] = 0
        session.save()
        latest = self.issue()
        self.client.post(old)
        self.assertNotIn('employer_verified_email', self.client.session)
        key = self.client.session.session_key
        self.client.post(latest)
        self.assertNotEqual(key, self.client.session.session_key)
        self.assertEqual(self.client.session.get_expiry_age(), 3600)

    def test_csrf_and_http_methods(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/employer/access/')
        token = client.cookies['csrftoken'].value
        client.post(
            '/employer/access/',
            {'email': 'csrf@example.invalid', 'csrfmiddlewaretoken': token},
        )
        link = client.session['employer_test_message']['link']
        self.assertEqual(client.post(link).status_code, 403)
        self.assertEqual(client.post('/employer/logout/').status_code, 403)
        self.assertEqual(client.get('/employer/logout/').status_code, 405)
        self.assertEqual(client.put(link, HTTP_X_CSRFTOKEN=token).status_code, 405)
