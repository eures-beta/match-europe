"""Candidate declarations, using the versioned ESCO pilot, without scoring.

Sector grouping and the behaviour shortlist are editorial. They never imply an
official ESCO hierarchy, a qualification or an occupation requirement.
"""

from functools import lru_cache
import json
from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _

from eures_beta.occupations.skills_pilot import catalogue

VERSION = 'esco-1.2.1-match-europe-50-v1'
FIELDS = ('acquired_skills', 'learning_activities', 'professional_behaviours')
CATEGORIES = {
    'cleaning': _('Cleaning and maintenance'),
    'agriculture': _('Agriculture and green spaces'),
    'hospitality': _('Hospitality and catering'),
    'security': _('Security'),
    'food': _('Food production'),
    'retail': _('Retail'),
    'transport': _('Transport and logistics'),
    'construction': _('Construction'),
    'industry': _('Industry and maintenance'),
    'care': _('Care and support'),
    'office': _('Office work'),
    'behaviours': _('Working with others and organising work'),
}


@lru_cache(maxsize=1)
def skill_groups():
    cards, skills = catalogue()
    sectors = json.loads(Path(__file__).with_name('skill_categories.json').read_text())
    if set(sectors['occupations']) != set(cards) or not set(
        sectors['occupations'].values()
    ) <= set(CATEGORIES):
        raise ValueError(
            'Candidate sector mapping does not match the versioned catalogue'
        )
    groups = {'acquired_skills': {}, 'professional_behaviours': {}}
    for card in cards.values():
        for source, target in (
            ('keySkills', 'acquired_skills'),
            ('behaviours', 'professional_behaviours'),
        ):
            for item in card[source]:
                groups[target].setdefault(
                    item['skillUri'],
                    (
                        'behaviours'
                        if source == 'behaviours'
                        else sectors['occupations'][card['id']]
                    ),
                )
    # An editorial behaviour must not silently become a technical activity.
    for uri in groups['professional_behaviours']:
        groups['acquired_skills'].pop(uri, None)
    return groups, skills


def skill_choices(name, language):
    groups, skills = skill_groups()
    group = groups['acquired_skills' if name == 'learning_activities' else name]
    return sorted(
        [(uri, skills[uri]['labels'][language]) for uri in group],
        key=lambda item: item[1].casefold(),
    )


def selection_field(label):
    return forms.MultipleChoiceField(
        label=label, required=False, widget=forms.CheckboxSelectMultiple
    )


def configure(form, language):
    for name in FIELDS:
        form.fields[name].choices = skill_choices(name, language)


def clean_selection(form, data, *, partial=False):
    """Shared by the questionnaire, pending registration and durable model."""
    mode = data.get('project_mode') or 'occupation'
    data['project_mode'] = mode
    if mode != 'open':
        for name in FIELDS:
            data[name] = []
        data['skill_catalogue_version'] = ''
        return
    data['occupation_references'] = []
    data['desired_occupations'] = ''
    data['occupation_query'] = ''
    data['skill_catalogue_version'] = VERSION
    for name, maximum in zip(FIELDS, (10, 5, 3)):
        values = data.get(name, [])
        if len(values) != len(set(values)):
            form.add_error(name, _('Select each item only once.'))
        if len(values) > maximum:
            form.add_error(
                name, _('Choose no more than %(maximum)s items.') % {'maximum': maximum}
            )
    if (
        not partial
        and not data.get('acquired_skills')
        and not data.get('learning_activities')
    ):
        form.add_error(
            'acquired_skills',
            _(
                'Choose at least one skill you can use or one activity you want to learn.'
            ),
        )
    if not partial and len(data.get('professional_behaviours', [])) != 3:
        form.add_error(
            'professional_behaviours',
            _('Choose exactly three professional behaviours.'),
        )
    if set(data.get('acquired_skills', [])) & set(data.get('learning_activities', [])):
        form.add_error(
            'learning_activities',
            _(
                'Choose an activity either as a skill you can use or as an activity to learn, not both.'
            ),
        )


def sections(form, language):
    """Render every URI once per section, with locale-specific search synonyms."""
    groups, skills = skill_groups()
    result = []
    for name, maximum in zip(FIELDS, (10, 5, 3)):
        bound = form[name]
        selected = set(bound.value() or [])
        categories = {}
        group = groups['acquired_skills' if name == 'learning_activities' else name]
        for index, (uri, label) in enumerate(form.fields[name].choices):
            item = {
                'uri': uri,
                'label': label,
                'id': f'id_{name}_{index}',
                'checked': uri in selected,
                'search': ' '.join(
                    [label, *skills[uri]['alternativeLabels'][language]]
                ),
            }
            categories.setdefault(group[uri], []).append(item)
        result.append(
            {
                'name': name,
                'label': bound.label,
                'errors': bound.errors,
                'maximum': maximum,
                'count': len(selected),
                'selected': [
                    item
                    for items in categories.values()
                    for item in items
                    if item['checked']
                ],
                'categories': [
                    {'label': CATEGORIES[key], 'items': items}
                    for key, items in categories.items()
                ],
            }
        )
    return result
