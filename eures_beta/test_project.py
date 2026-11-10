from html.parser import HTMLParser

from django.test import SimpleTestCase, override_settings


class ProjectLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'h1':
            self.headings += 1
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])


class ProjectPageTests(SimpleTestCase):
    def test_historical_content_and_qualifications_in_all_languages(self):
        samples = {
            'fr': (
                'Connecter les talents et les emplois d’un même bassin économique',
                'Le principal frein n’est pas le matching.',
                'Cet horizon n’est pas un quota imposé à chaque partenaire.',
                'Il ne correspond pas à un cas réel identifié.',
                'Sources et données à consolider',
                'sans préjuger de son activation',
            ),
            'en': (
                'Connecting talent and jobs across a shared economic area',
                'The main obstacle is not matching.',
                'This horizon is not a quota imposed on each partner.',
                'It does not refer to an identified real case.',
                'Sources and data still to be consolidated',
                'WhatsApp Business',
            ),
            'de': (
                'Talente und Arbeitsplätze in einem gemeinsamen Wirtschaftsraum zusammenführen',
                'Match Europe',
                'WhatsApp Business',
                '300',
            ),
        }
        for language, texts in samples.items():
            with self.subTest(language=language):
                response = self.client.get('/project/', {'lang': language})
                for text in texts:
                    self.assertContains(response, text)
                links = ProjectLinks()
                links.feed(response.content.decode())
                self.assertEqual(links.headings, 1)
                self.assertEqual(len(links.ids), len(set(links.ids)))
                self.assertEqual(
                    len(links.anchors), 16
                )  # Skip link and 15 contents links.
                self.assertTrue(set(links.anchors).issubset(links.ids))
                self.assertContains(response, f'/candidate/?lang={language}')
                self.assertContains(response, f'/employer/pages/{language}.html')
                self.assertNotContains(response, 'id="app"')

    def test_fallback_language_and_safe_methods(self):
        response = self.client.get('/project/?lang=unknown')
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, 'Présentation institutionnelle')
        self.assertEqual(self.client.head('/project/').status_code, 200)
        self.assertEqual(self.client.post('/project/').status_code, 405)
