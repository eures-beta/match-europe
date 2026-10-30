"""Catch long minified HTML blocks which djLint can leave unchanged."""

from html.parser import HTMLParser
from pathlib import Path
import re


def compact_lines(text):
    # Template expressions are not HTML. Keep their line positions unchanged.
    masked = re.sub(
        r'{%.*?%}|{{.*?}}',
        lambda match: re.sub(r'[^\n]', ' ', match[0]),
        text,
        flags=re.S,
    )

    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.raw = None
            self.openings = {}

        def handle_starttag(self, tag, attrs):
            if self.raw:
                return
            if tag in ('script', 'style', 'pre', 'textarea'):
                self.raw = tag
                return
            if tag not in (
                'form',
                'select',
                'option',
                'button',
                'input',
                'label',
                'nav',
                'div',
                'header',
                'ul',
                'li',
                'section',
                'main',
                'article',
                'fieldset',
                'legend',
                'table',
                'tr',
                'td',
                'th',
            ):
                return
            line = self.getpos()[0]
            self.openings[line] = self.openings.get(line, 0) + 1

        def handle_endtag(self, tag):
            if tag == self.raw:
                self.raw = None

    parser = Elements()
    parser.feed(masked)
    return [
        number
        for number, line in enumerate(text.splitlines(), 1)
        if len(line) > 120 and parser.openings.get(number, 0) > 1
    ]


def main():
    failed = False
    for path in sorted(Path('eures_beta').rglob('*.html')):
        for line in compact_lines(path.read_text()):
            print(
                f'{path}:{line}: split this long line containing multiple HTML elements'
            )
            failed = True
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
