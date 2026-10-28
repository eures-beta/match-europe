from eures_beta.choices import MOBILITY
from django import forms
from django.utils.translation import gettext_lazy as _
from eures_beta.candidates.models import Candidate


class CandidateForm(forms.ModelForm):
    cross_border = forms.ChoiceField(
        label=_(
            'Would you work in another country while keeping your current residence?'
        ),
        choices=MOBILITY,
    )
    relocation = forms.ChoiceField(
        label=_('Would you move to another country for a job?'), choices=MOBILITY
    )

    def __init__(self, *args, complete=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not complete:
            for field in self.fields.values():
                field.required = False

    class Meta:
        model = Candidate
        fields = [
            'name',
            'experience',
            'jobs',
            'skills',
            'languages',
            'location',
            'availability',
            'cross_border',
            'relocation',
        ]
        labels = {
            'name': _('Name'),
            'experience': _('Experience'),
            'jobs': _('Jobs sought'),
            'skills': _('Skills'),
            'languages': _('Languages'),
            'location': _('Residence'),
            'availability': _('Availability'),
        }
        widgets = {'experience': forms.Textarea(attrs={'rows': 7})}
