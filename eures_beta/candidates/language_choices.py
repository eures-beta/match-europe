"""Validated language declarations; ISO codes and CEFR levels, without inference."""

from django import forms
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODES = frozenset(
    "aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu".split()
)
LEVELS = frozenset(('A1', 'A2', 'B1', 'B2', 'C1', 'C2'))


class LanguageSkillsField(forms.JSONField):
    def __init__(self, **kwargs):
        super().__init__(
            label=_('Languages I can use'),
            required=False,
            widget=forms.HiddenInput,
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        if value in (None, ''):
            return {'status': 'unspecified', 'languages': []}
        invalid = forms.ValidationError(
            _('Choose each language and its level, or select the discussion option.')
        )
        if not isinstance(value, dict) or set(value) != {'status', 'languages'}:
            raise invalid
        rows = value['languages']
        if (
            value['status'] not in ('unspecified', 'specified', 'discuss')
            or not isinstance(rows, list)
            or len(rows) > 20
        ):
            raise invalid
        if (value['status'] == 'specified') != bool(rows):
            raise invalid
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'code', 'level'}:
                raise invalid
            code, level = row['code'], row['level']
            if (
                not isinstance(code, str)
                or not isinstance(level, str)
                or code not in LANGUAGE_CODES
                or level not in LEVELS
                or code in seen
            ):
                raise invalid
            seen.add(code)
        return {
            'status': value['status'],
            'languages': [{'code': row['code'], 'level': row['level']} for row in rows],
        }


def upgrade_language_answers(data):
    previous = [
        (code, data.pop(name))
        for name, code in [
            ('french_level', 'fr'),
            ('english_level', 'en'),
            ('german_level', 'de'),
        ]
        if name in data
    ]
    if previous and 'language_skills' not in data:
        rows = [
            {'code': code, 'level': level}
            for code, level in previous
            if level in LEVELS
        ]
        data['language_skills'] = {
            'status': 'specified' if rows else 'unspecified',
            'languages': rows,
        }
        notes = [
            {'code': code, 'value': level}
            for code, level in previous
            if level and level not in LEVELS
        ]
        if notes:
            data['language_notes'] = notes
