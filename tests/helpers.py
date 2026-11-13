"""HTML assertions independent of attribute order and indentation."""

from html.parser import HTMLParser


def json_scripts(response):
    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__()
            self.current = None
            self.values = {}

        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            if (
                tag == 'script'
                and attrs.get('type') == 'application/json'
                and attrs.get('id')
            ):
                self.current = attrs['id']
                self.values[self.current] = ''

        def handle_data(self, data):
            if self.current:
                self.values[self.current] += data

        def handle_endtag(self, tag):
            if tag == 'script':
                self.current = None

    scripts = Scripts()
    scripts.feed(response.content.decode())
    return scripts.values


def assert_active_link(testcase, response, href):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.found = False

        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            classes = attrs.get('class', '').split()
            if (
                tag == 'a'
                and attrs.get('href') == href
                and 'lang-link' in classes
                and 'is-active' in classes
            ):
                self.found = True

    links = Links()
    links.feed(response.content.decode())
    testcase.assertTrue(links.found, f'No active language link to {href}')
