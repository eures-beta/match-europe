"""Assertions on decoded MIME, without relying on a mail client's auto-linking."""

import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlsplit


class Links(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.hrefs = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href"))


def assert_clickable_email(test, message):
    mime = BytesParser(policy=policy.default).parsebytes(message.message().as_bytes())
    test.assertEqual(mime.get_content_type(), "multipart/alternative")
    text, html = list(mime.iter_parts())
    test.assertEqual(text.get_content_type(), "text/plain")
    test.assertEqual(html.get_content_type(), "text/html")
    test.assertEqual(text.get_content().strip(), message.body.strip())
    test.assertIn('bgcolor="#004494"', html.get_content())
    urls = re.findall(r"https://[^\s<>]+", message.body)
    test.assertTrue(urls)
    hrefs = Links(html.get_content()).hrefs
    for url in urls:
        expected = urlsplit(url)
        # Django percent-encodes reserved characters such as ':' inside a query.
        # Compare the actual destination and decoded token, not its spelling.
        test.assertTrue(
            any(
                (actual.scheme, actual.netloc, actual.path, actual.fragment)
                == (expected.scheme, expected.netloc, expected.path, expected.fragment)
                and parse_qsl(actual.query) == parse_qsl(expected.query)
                for actual in map(urlsplit, hrefs)
            ),
            "The HTML alternative must retain each complete destination and token.",
        )
