"""Canonical candidate occupation references; ESCO and ROME remain independent."""

import re
from django.utils.translation import gettext_lazy as _
from eures_beta.occupations.catalog import (
    occupation_index,
    present,
    references,
    rome_catalog,
    rome_suggestions,
    suggestions,
)


def resolve_reference(value, language):
    if not isinstance(value, str):
        return None
    if value.startswith('esco:'):
        row = occupation_index().get(value[5:])
        if row:
            job = present(row, language)
            return {
                'value': value,
                'label': 'ESCO — ' + job['label'],
                'description': job['description'],
                'version': '1.2.1',
            }
    elif value.startswith('rome:'):
        row = rome_catalog()['fiches'].get(value[5:])
        if row:
            return {
                'value': value,
                'label': 'ROME ' + row['code'] + ' — ' + row['label'],
                'description': '',
                'version': '26M10',
            }
    return None


def search_occupations(query, language):
    query = query.strip()
    if not 2 <= len(query) <= 150:
        return []
    is_rome = bool(re.fullmatch(r'(?:ROME\s*[:—-]?\s*)?[A-Z]\d{4}', query, re.I))
    is_reference = bool(
        re.fullmatch(
            r'(?:ESCO\s*[:—-]?\s*.+|\d+(?:\.\d+)+|[0-9a-f-]{36}|https?://data\.europa\.eu/esco/occupation/[0-9a-f-]{36})',
            query,
            re.I,
        )
    )
    esco = (
        []
        if is_rome
        else (
            references(query, language)
            if is_reference
            else suggestions(query, language)
        )
    )
    return [resolve_reference('esco:' + row['uri'], language) for row in esco[:20]] + [
        resolve_reference('rome:' + row['code'], language)
        for row in rome_suggestions(query)
    ]
