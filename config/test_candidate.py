from unittest.mock import patch

from django.test import SimpleTestCase, override_settings


@override_settings(SHARED_DEMO=True, DEMO_MODE=True)
class CandidateEntryTests(SimpleTestCase):
    def test_navigation_preserves_supported_languages_and_rejects_other_targets(self):
        for language in ('fr', 'en', 'de', 'https://example.invalid'):
            expected = language if language in ('fr', 'en', 'de') else 'fr'
            response = self.client.get(
                '/forms/eures-beta/candidate', {'lang': language}, secure=True
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url, f'/previews/employer-landing/candidate-{expected}.html'
            )

    def test_screen_has_three_choices_and_never_activates_employer_api(self):
        titles = {
            'fr': 'Trouvez votre prochain emploi en Europe',
            'en': 'Find your next job in Europe',
            'de': 'Finden Sie Ihren nächsten Job in Europa',
        }
        for language, title in titles.items():
            with self.subTest(language=language):
                response = self.client.get(
                    f'/previews/employer-landing/candidate-{language}.html',
                    secure=True,
                )
                body = b''.join(response.streaming_content).decode()
                self.assertIn(title, body)
                self.assertEqual(body.count('data-candidate-choice='), 3)
                self.assertNotIn('data-live-local', body)
                self.assertNotIn('data-employer-account', body)
                self.assertNotIn('<form', body)
                for target in ('fr', 'en', 'de'):
                    self.assertIn(f'href="candidate-{target}.html"', body)

    def test_assets_are_served_with_correct_types_and_no_arbitrary_file_access(self):
        for asset, content_type in [('css', 'text/css'), ('js', 'text/javascript')]:
            response = self.client.get(
                f'/previews/employer-landing/candidate.{asset}', secure=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], content_type)
            response.close()
        for path in ('candidate-copy.json', 'candidate.py', 'candidate-es.html'):
            self.assertEqual(
                self.client.get(
                    '/previews/employer-landing/' + path, secure=True
                ).status_code,
                404,
            )

    def test_preview_cannot_receive_uploads_or_bypass_demo_gate(self):
        url = '/previews/employer-landing/candidate-fr.html'
        self.assertEqual(self.client.post(url, secure=True).status_code, 405)
        self.assertEqual(self.client.get(url).status_code, 404)
        with override_settings(DEMO_MODE=False):
            self.assertEqual(self.client.get(url, secure=True).status_code, 404)
        with override_settings(SHARED_DEMO=False):
            with patch.dict('os.environ', {'ME_EMPLOYER_LOCAL_API': '1'}):
                self.assertEqual(
                    self.client.get(url, REMOTE_ADDR='192.0.2.42').status_code, 404
                )
