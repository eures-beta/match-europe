from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Candidate, Offer, Question

MOBILITY = [
    ('', _('Please choose')),
    ('yes', _('Yes')),
    ('no', _('No')),
    ('discuss', _('To discuss')),
]


class AccessForm(forms.Form):
    email = forms.EmailField(label=_('Email'), max_length=150)


class UploadForm(forms.Form):
    document = forms.FileField(
        label=_('PDF document'),
        widget=forms.ClearableFileInput(attrs={'accept': 'application/pdf'}),
    )
    agreement = forms.BooleanField(
        label=_(
            'I agree to the processing of this document to prepare my recruitment journey.'
        )
    )

    def clean_document(self):
        value = self.cleaned_data['document']
        if value.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('The PDF must be smaller than 10 MB.'))
        if not value.name.lower().endswith('.pdf') or value.read(5) != b'%PDF-':
            raise forms.ValidationError(_('Please provide a valid PDF.'))
        value.seek(0)
        return value


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


class ReviewForm(forms.Form):
    note = forms.CharField(
        label=_('Review note'),
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )


class EmployerContactForm(forms.Form):
    name = forms.CharField(label=_('Contact name'), max_length=150)
    email = forms.EmailField(label=_('Contact email'), max_length=254)
    phone = forms.CharField(label=_('Phone (optional)'), max_length=40, required=False)
    function = forms.CharField(
        label=_('Role in the company (optional)'), max_length=150, required=False
    )


class ImportAssignmentForm(forms.Form):
    adviser = forms.ModelChoiceField(
        label=_('Adviser responsible for this offer'),
        queryset=None,
        required=False,
        empty_label=_('Unassigned'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model

        self.fields['adviser'].queryset = (
            get_user_model()
            .objects.filter(
                is_active=True, profile__role='adviser', profile__verified=True
            )
            .select_related('profile')
            .order_by('profile__name', 'pk')
        )
        self.fields['adviser'].label_from_instance = (
            lambda user: user.profile.name or user.username
        )
