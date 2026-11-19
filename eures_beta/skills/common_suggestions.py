"""Shared, bounded shortlist and persistent cache for both roles."""

from datetime import timedelta
from uuid import uuid4
from django.conf import settings
from django.db import transaction
from eures_beta.occupations import unified
from eures_beta.occupations.catalog import normalize
from django.utils import timezone
from . import albert_skills, common_source, baker_mixed
from .models import OccupationSkillSuggestion
from .skills_pilot import catalogue


def cached_selection(source):
    key = {
        'occupation_uri': source['key'],
        'source_version': source['version'],
        'method': 'common-shortlist-v2:' + albert_skills.method(),
    }
    technical = {
        uri: kind
        for uri, kind in source['relations'].items()
        if source['skills'][uri]['kind'] == 'skill'
        and source['skills'][uri].get('skillType') != 'knowledge'
    }

    def validate(values):
        values = albert_skills.validate(values, technical)
        seen = set()
        result = []
        for value in values:
            wording = normalize(source['skills'][value]['labels']['fr'])
            if wording not in seen:
                result.append(value)
                seen.add(wording)
        return result

    if not albert_skills.enabled():
        return None, False
    lease = uuid4()
    with transaction.atomic():
        record, created = OccupationSkillSuggestion.objects.get_or_create(**key)
        record = OccupationSkillSuggestion.objects.select_for_update().get(pk=record.pk)
        if record.status == 'ready':
            try:
                return validate(record.skill_uris), False
            except albert_skills.SuggestionUnavailable:
                record.status = 'failed'
                record.save(update_fields=['status', 'updated_at'])
        if not created and record.updated_at > timezone.now() - timedelta(seconds=60):
            return None, True
        record.status, record.lease = 'pending', lease
        record.save()
    try:
        values = validate(
            albert_skills.ask(
                source['key'],
                source['skills'],
                technical,
                occupation_label=source['occupation']['label'],
            )
        )
    except albert_skills.SuggestionUnavailable:
        OccupationSkillSuggestion.objects.filter(pk=record.pk, lease=lease).update(
            status='failed', updated_at=timezone.now()
        )
        return None, True
    if not OccupationSkillSuggestion.objects.filter(pk=record.pk, lease=lease).update(
        skill_uris=values, status='ready', updated_at=timezone.now()
    ):
        return None, True
    return values, False


def preserve_selection(card, selection, source):
    if selection is None:
        return card
    if not isinstance(selection, dict):
        raise ValueError('Invalid selected skills')
    for name, group, kind, maximum in [
        ('skills', 'keySkills', 'skill', 5),
        ('behaviours', 'behaviours', 'behaviour', 3),
    ]:
        keys = selection.get(name, [])
        if (
            not isinstance(keys, list)
            or len(keys) > maximum
            or len(set(key for key in keys if isinstance(key, str))) != len(keys)
        ):
            raise ValueError('Invalid selected skills')
        if any(
            key not in source['skills'] or source['skills'][key]['kind'] != kind
            for key in keys
        ):
            raise ValueError('Unknown selected skill')
        offered = {row['skillUri'] for row in card[group]}
        card[group] += [{'skillUri': key} for key in keys if key not in offered]
        for key in keys:
            card['_skills'].setdefault(key, source['skills'][key])
    return card


def card(reference, *, generate=True, selection=None):
    source = common_source.source_for(reference)
    # The explicitly tested baker reading aids remain available to both roles.
    baker = baker_mixed.card(source['key'])
    if baker:
        return preserve_selection(
            {**baker, 'commonSource': source, 'shortlistMethod': 'reviewed_baker'},
            selection,
            source,
        )
    cards, _ = catalogue()
    prepared = next(
        (card for card in cards.values() if card['occupation']['uri'] == source['key']),
        None,
    )
    generated = False
    unavailable = False
    if prepared:
        values = [
            row['skillUri']
            for row in prepared['keySkills']
            if row['skillUri'] in source['skills']
        ]
        # Existing prepared skills retain their order; add complementary ROME choices.
        known_wording = {
            normalize(source['skills'][key]['labels']['fr']) for key in values
        }
        extras = [
            key
            for key in common_source.balanced(source)
            if key not in values
            and source['skills'][key]['scheme'] == 'ROME'
            and normalize(source['skills'][key]['labels']['fr']) not in known_wording
        ]
        values += extras[:4]
        method = 'prepared'
    else:
        values, unavailable = cached_selection(source) if generate else (None, False)
        generated = values is not None
        method = 'albert' if generated else 'official_priority'
        values = values or common_source.balanced(source)
    behaviours = common_source.ordered(source, 'behaviour')
    # Showing fewer than the whole behavioural union is a reading aid, not a requirement.
    behaviours = behaviours[:8]
    if not values:
        raise ValueError('No official technical skills')
    return preserve_selection(
        {
            'occupation': {
                'uri': source['key'],
                'labels': {
                    lang: unified.resolve_reference(source['key'], lang)['label']
                    for lang in ('fr', 'en', 'de')
                },
            },
            'keySkills': [{'skillUri': key} for key in values],
            'behaviours': [{'skillUri': key} for key in behaviours],
            '_skills': source['skills'],
            'commonSource': source,
            'shortlistMethod': method,
            'generated': generated,
            'unavailable': unavailable,
            'simulated': generated and settings.ALBERT_SIMULATED,
        },
        selection,
        source,
    )
