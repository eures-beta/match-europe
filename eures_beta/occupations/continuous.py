"""Reference choices shared by the real forms, never inferred declarations."""

from zipfile import BadZipFile
from django.conf import settings
from . import albert_skills
from .catalog import occupation_index
from .skill_source import source_for
from .skills_pilot import catalogue


def enabled():
    return settings.CONTINUOUS_SKILLS_ENABLED


def trial_request(request):
    # Compatibility name: availability is independent of deployment or client IP.
    return enabled()


def reference_card(uri, *, generate=False):
    cards, _ = catalogue()
    existing = next(
        (card for card in cards.values() if card['occupation']['uri'] == uri), None
    )
    return existing or albert_skills.resolve(uri, generate=generate)


def validated_selection(value, occupations):
    if not isinstance(value, dict) or len(value) > 35 or set(value) - set(occupations):
        raise ValueError('Invalid occupation skills')
    result = {}
    cards, _ = catalogue()
    indexed = {card['occupation']['uri']: card for card in cards.values()}
    for uri, selection in value.items():
        if uri not in occupation_index() or not isinstance(selection, dict):
            raise ValueError('Invalid occupation skills')
        if uri in indexed:
            allowed = {
                name: {item['skillUri'] for item in indexed[uri][group]}
                for name, group in [
                    ('skills', 'keySkills'),
                    ('behaviours', 'behaviours'),
                ]
            }
        else:
            try:
                _, linked = source_for(uri)
            except (OSError, ValueError, KeyError, BadZipFile):
                raise ValueError('Verified skill source unavailable') from None
            allowed = {'skills': set(linked), 'behaviours': set()}
        cleaned = {}
        for name, maximum in [('skills', 5), ('behaviours', 3)]:
            values = selection.get(name, [])
            if (
                not isinstance(values, list)
                or len(values) > maximum
                or any(
                    not isinstance(key, str) or key not in allowed[name]
                    for key in values
                )
                or len(set(values)) != len(values)
            ):
                raise ValueError('Invalid occupation skills')
            cleaned[name] = values
        if cleaned['skills'] or cleaned['behaviours']:
            result[uri] = {**cleaned, 'version': 'ESCO 1.2.1'}
    return result


def summary(value, language):
    lines = []
    _, known = catalogue()
    for uri, selection in (value or {}).items():
        job = occupation_index().get(uri)
        if not job:
            continue
        skills = known
        selected = selection.get('skills', []) + selection.get('behaviours', [])
        if any(key not in skills for key in selected):
            try:
                skills, _ = source_for(uri)
            except (OSError, ValueError, KeyError, BadZipFile):
                continue
        labels = [skills[key]['labels'][language] for key in selected if key in skills]
        if labels:
            lines.append(job['labels'][language] + ' : ' + ', '.join(labels))
    return '\n'.join(lines)
