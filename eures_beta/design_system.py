"""Read the design-system tokens for the reference page and its tests; no business logic."""

import math
import re
from pathlib import Path

DESIGN_SYSTEM_DIR = Path(__file__).resolve().parent / 'static' / 'design-system'
TOKENS = DESIGN_SYSTEM_DIR / 'tokens.css'

COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
DECLARATION = re.compile(r'(--me-[a-z0-9-]+)\s*:\s*([^;]+);')
TOKEN_USE = re.compile(r'var\(\s*(--me-[a-z0-9-]+)')
RAW_COLOUR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(')
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
WHITE = '#ffffff'


def read_css(path):
    return COMMENT.sub('', path.read_text(encoding='utf-8'))


THEMES_DIR = DESIGN_SYSTEM_DIR / 'themes'
DIRECTIONS = ('eures', 'continuite', 'hybride')


def css_files():
    """Every stylesheet of the design system, themes included."""
    return sorted(DESIGN_SYSTEM_DIR.rglob('*.css'))


def _declarations(path):
    return {name: value.strip() for name, value in DECLARATION.findall(read_css(path))}


def token_declarations(direction='eures'):
    """Tokens of tokens.css, with a direction's overrides applied on top."""
    declarations = _declarations(TOKENS)
    if direction != 'eures':
        declarations.update(_declarations(THEMES_DIR / f'{direction}.css'))
    return declarations


def resolve(name, declarations):
    """Follow var(--me-...) references until a raw value."""
    value = declarations[name]
    seen = {name}
    while match := TOKEN_USE.match(value):
        reference = match[1]
        if reference in seen:
            raise ValueError(f'circular token reference at {reference}')
        seen.add(reference)
        value = declarations[reference]
    return value


def contrast(foreground, background=WHITE):
    """WCAG 2.1 contrast ratio between two #rrggbb colours."""

    def luminance(colour):
        channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


# Text colours made for a coloured background, measured on that background, not on white.
TEXT_BACKGROUNDS = {
    '--me-color-text-inverse': '--me-color-action',
    '--me-color-action-text': '--me-color-action',
    '--me-color-accent-text': '--me-color-accent',
}


def colour_tokens(prefix, direction='eures'):
    """Colour tokens with their raw value and contrast on their background, in file order."""
    declarations = token_declarations(direction)
    rows = []
    for name in declarations:
        if not name.startswith(prefix) or name.endswith('-rgb'):
            continue
        value = resolve(name, declarations)
        if not HEX.match(value):
            continue
        reference = declarations[name]
        background = TEXT_BACKGROUNDS.get(name, '')
        background_value = resolve(background, declarations) if background else WHITE
        rows.append(
            {
                'name': name,
                'value': value.lower(),
                'reference': reference if reference != value else '',
                'background': background,
                # Rounded down: 4.46 must not read as a passing 4.5.
                'contrast': math.floor(contrast(value, background_value) * 10) / 10,
            }
        )
    return rows


def scale_tokens(prefix):
    declarations = token_declarations()
    return [
        {'name': name, 'value': value}
        for name, value in declarations.items()
        if name.startswith(prefix)
    ]
