"""Reference choices shared by the real forms, never inferred declarations."""

from zipfile import BadZipFile
from . import albert_skills
from eures_beta.occupations.catalog import occupation_index
from .skill_source import source_for
from .skills_pilot import catalogue


def reference_card(uri, *, generate=False):
    cards, _ = catalogue()
    existing = next(
        (card for card in cards.values() if card['occupation']['uri'] == uri), None
    )
    return existing or albert_skills.resolve(uri, generate=generate)


def validated_selection(value, occupations, *, mixed=False):
    from . import common_source
    from eures_beta.occupations import unified

    if not isinstance(value, dict) or len(value) > 35:
        raise ValueError('Invalid occupation skills')
    allowed_jobs = {unified.canonical(ref) for ref in occupations}
    result = {}
    for reference, selection in value.items():
        key = unified.canonical(reference)
        if key not in allowed_jobs or not isinstance(selection, dict):
            raise ValueError('Invalid occupation skills')
        source = common_source.source_for(key)
        cleaned = {}
        for name, kind, maximum in [
            ('skills', 'skill', 5),
            ('behaviours', 'behaviour', 3),
        ]:
            values = selection.get(name, [])
            if (
                not isinstance(values, list)
                or len(values) > maximum
                or any(
                    not isinstance(item, str)
                    or item not in source['skills']
                    or source['skills'][item]['kind'] != kind
                    for item in values
                )
                or len(set(values)) != len(values)
            ):
                raise ValueError('Invalid occupation skills')
            previous = result.get(key, {}).get(name, [])
            cleaned[name] = list(dict.fromkeys(previous + values))
            if len(cleaned[name]) > maximum:
                raise ValueError('Invalid occupation skills')
        if cleaned['skills'] or cleaned['behaviours']:
            result[key] = {**cleaned, **common_source.metadata(source, cleaned)}
    return result


def summary(value, language):
    from . import common_source
    from eures_beta.occupations import unified

    lines = []
    _, known = catalogue()
    for ref, selection in (value or {}).items():
        job = unified.resolve_reference(ref, language)
        if not job:
            continue
        try:
            source = common_source.source_for(ref)
        except (ValueError, OSError, KeyError, BadZipFile):
            source = {'skills': known}
        keys = selection.get('skills', []) + selection.get('behaviours', [])
        labels = [
            source['skills'][key]['labels'].get(
                language, source['skills'][key]['labels']['fr']
            )
            for key in keys
            if key in source['skills']
        ]
        if labels:
            lines.append(job['label'] + ' : ' + ', '.join(labels))
    return '\n'.join(lines)
