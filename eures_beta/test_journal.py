from html.parser import HTMLParser

from django.test import SimpleTestCase, override_settings


class JournalMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.articles = 0
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])
        self.articles += tag == 'article'
        self.h1 += tag == 'h1'


@override_settings(DEMO_MODE=False)
class JournalTests(SimpleTestCase):
    def test_full_history_and_new_milestones_are_translated_and_public(self):
        samples = {
            'fr': (
                'Début octobre 2026',
                'Aucune démarche d’acquisition',
                'un tiers du temps',
                'La confiance devient le principal enjeu',
            ),
            'en': (
                'Early October 2026',
                'No acquisition campaign',
                'one third',
                'Trust becomes the main issue',
            ),
            'de': (
                'Anfang Oktober 2026',
                'keine Akquisekampagne',
                'ein Drittel',
                'Vertrauen wird zum zentralen Thema',
            ),
        }
        for language, texts in samples.items():
            with self.subTest(language=language):
                response = self.client.get('/journal/', {'lang': language})
                self.assertTemplateUsed(response, 'journal.html')
                for text in texts:
                    self.assertContains(response, text)
                self.assertContains(response, 'ADEM')
                self.assertContains(response, 'FOREM')
                self.assertNotContains(response, '1 012')
                self.assertNotContains(response, '2026-11-02')
                parser = JournalMarkup()
                parser.feed(response.content.decode())
                self.assertEqual(parser.articles, 15)
                self.assertEqual(parser.h1, 1)
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                self.assertTrue(set(parser.anchors).issubset(parser.ids))
                self.assertLess(
                    response.content.index(b'id="entry-2026-10-01"'),
                    response.content.index(b'id="entry-2026-09-04"'),
                )
                self.assertLess(
                    response.content.index(b'id="entry-2026-09-04"'),
                    response.content.index(b'id="entry-2026-08-17"'),
                )

    def test_fallback_and_safe_methods(self):
        response = self.client.get('/journal/?lang=unknown')
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, 'Début octobre 2026')
        self.assertEqual(self.client.head('/journal/').status_code, 200)
        self.assertEqual(self.client.post('/journal/').status_code, 405)
