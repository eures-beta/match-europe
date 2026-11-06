"""Local review catalogue. Editorial choices never become official ESCO relations."""

from functools import lru_cache
import json
from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _

DATA = Path(__file__).parent / 'data'
KEY_MAX = 5
BEHAVIOUR_MAX = 3


@lru_cache(maxsize=1)
def catalogue():
    pilot = json.loads((DATA / 'skills_pilot.json').read_text())
    source = json.loads((DATA / 'skills_pilot_sources.json').read_text())
    skills = {item['uri']: item for item in source['skills']}
    official = {
        (r['occupationUri'], r['skillUri'], r['relationType'])
        for r in source['occupationSkillRelations']
    }
    cards = {card['id']: card for card in pilot['cards']}
    alternative = pilot['cleaningAlternative']
    cards['nettoyage-locaux'] = {
        **cards['nettoyage'],
        'id': 'nettoyage-locaux',
        'occupation': alternative['occupation'],
        'keySkills': alternative['keySkills'],
    }
    # Behavioural suggestions from the domestic variant stay editorial, not official.
    for card in cards.values():
        for item in card['keySkills']:
            relation = item['occupationRelation']['type']
            if (card['occupation']['uri'], item['skillUri'], relation) not in official:
                raise ValueError('Missing official occupation–skill relation')
        for group in ('keySkills', 'behaviours'):
            for item in card[group]:
                if not all(
                    skills[item['skillUri']]['labels'].get(lang)
                    for lang in ('fr', 'en', 'de')
                ):
                    raise ValueError('Missing official translation')
    return cards, skills


def choices(card, group, language):
    _, skills = catalogue()
    return [
        (item['skillUri'], skills[item['skillUri']]['labels'][language])
        for item in card[group]
    ]


class SelectionForm(forms.Form):
    skills = forms.MultipleChoiceField(
        label=_('Key skills'), required=False, widget=forms.CheckboxSelectMultiple
    )
    behaviours = forms.MultipleChoiceField(
        label=_('Professional behaviours'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    other = forms.CharField(
        label=_('Another skill or behaviour (optional)'),
        required=False,
        max_length=300,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    occupation = forms.CharField(widget=forms.HiddenInput)
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)

    def __init__(self, card, language, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].choices = choices(card, 'keySkills', language)
        self.fields['behaviours'].choices = choices(card, 'behaviours', language)
        self.fields['other'].widget.attrs['class'] = 'form-control'

    def clean_skills(self):
        selected = self.cleaned_data['skills']
        if len(selected) != len(set(selected)) or len(selected) > KEY_MAX:
            raise forms.ValidationError(_('Choose up to 5 key skills.'))
        return selected

    def clean_behaviours(self):
        selected = self.cleaned_data['behaviours']
        if len(selected) != len(set(selected)) or len(selected) > BEHAVIOUR_MAX:
            raise forms.ValidationError(_('Choose up to 3 professional behaviours.'))
        return selected
