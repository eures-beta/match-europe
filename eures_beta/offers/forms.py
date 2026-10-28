from eures_beta.choices import MOBILITY
from django import forms
from django.utils.translation import gettext_lazy as _
from eures_beta.offers.models import Offer, Question


class OfferForm(forms.ModelForm):
    cross_border = forms.ChoiceField(
        label=_('Do you accept candidates who keep living in a neighbouring country?'),
        choices=MOBILITY,
    )
    relocation = forms.ChoiceField(
        label=_('Do you accept candidates who move from another country for this job?'),
        choices=MOBILITY,
    )

    def __init__(self, *args, complete=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not complete:
            for field in self.fields.values():
                field.required = False

    class Meta:
        model = Offer
        fields = [
            'title',
            'company',
            'location',
            'description',
            'contract',
            'salary',
            'hours',
            'languages',
            'skills',
            'cross_border',
            'relocation',
        ]
        labels = {
            'title': _('Job title'),
            'company': _('Company'),
            'location': _('Workplace'),
            'description': _('Job description'),
            'contract': _('Contract'),
            'salary': _('Salary'),
            'hours': _('Working hours'),
            'languages': _('Languages'),
            'skills': _('Skills'),
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 7})}


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'expectation', 'options', 'mandatory']
        labels = {
            'text': _('Question for the candidate'),
            'expectation': _('Expected answer or evaluation guideline'),
            'options': _('Quick answers separated by | (optional)'),
            'mandatory': _('Essential requirement — human review required'),
        }
