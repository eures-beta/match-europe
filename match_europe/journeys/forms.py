from django import forms
from .models import Candidate, Offer, Question
MOBILITY = [('', 'Please choose'), ('yes', 'Yes'), ('no', 'No'), ('discuss', 'To discuss')]

class AccessForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=150)

class UploadForm(forms.Form):
    document = forms.FileField(label='PDF document', widget=forms.ClearableFileInput(attrs={'accept': 'application/pdf'}))
    agreement = forms.BooleanField(label='I agree to the processing of this document to prepare my recruitment journey.')

    def clean_document(self):
        value = self.cleaned_data['document']
        if value.size > 10 * 1024 * 1024:
            raise forms.ValidationError('The PDF must be smaller than 10 MB.')
        if not value.name.lower().endswith('.pdf') or value.read(5) != b'%PDF-':
            raise forms.ValidationError('Please provide a valid PDF.')
        value.seek(0)
        return value

class OfferForm(forms.ModelForm):
    cross_border = forms.ChoiceField(label='Do you accept candidates who keep living in a neighbouring country?', choices=MOBILITY)
    relocation = forms.ChoiceField(label='Do you accept candidates who move from another country for this job?', choices=MOBILITY)

    def __init__(self, *args, complete=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not complete:
            for field in self.fields.values():
                field.required = False

    class Meta:
        model = Offer
        fields = ['title', 'company', 'location', 'description', 'contract', 'salary', 'hours', 'languages', 'skills', 'cross_border', 'relocation']
        labels = {'title': 'Job title', 'company': 'Company', 'location': 'Workplace', 'description': 'Job description', 'contract': 'Contract', 'salary': 'Salary', 'hours': 'Working hours', 'languages': 'Languages', 'skills': 'Skills'}
        widgets = {'description': forms.Textarea(attrs={'rows': 7})}

class CandidateForm(forms.ModelForm):
    cross_border = forms.ChoiceField(label='Would you work in another country while keeping your current residence?', choices=MOBILITY)
    relocation = forms.ChoiceField(label='Would you move to another country for a job?', choices=MOBILITY)

    def __init__(self, *args, complete=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not complete:
            for field in self.fields.values():
                field.required = False

    class Meta:
        model = Candidate
        fields = ['name', 'experience', 'jobs', 'skills', 'languages', 'location', 'availability', 'cross_border', 'relocation']
        labels = {'name': 'Name', 'experience': 'Experience', 'jobs': 'Jobs sought', 'skills': 'Skills', 'languages': 'Languages', 'location': 'Residence', 'availability': 'Availability'}
        widgets = {'experience': forms.Textarea(attrs={'rows': 7})}

class QuestionForm(forms.ModelForm):

    class Meta:
        model = Question
        fields = ['text', 'expectation', 'options', 'mandatory']
        labels = {'text': 'Question for the candidate', 'expectation': 'Expected answer or evaluation guideline', 'options': 'Quick answers separated by | (optional)', 'mandatory': 'Essential requirement — human review required'}

class MessageForm(forms.Form):
    body = forms.CharField(label='Your message', max_length=4000, widget=forms.Textarea(attrs={'rows': 3}))

class ReviewForm(forms.Form):
    note = forms.CharField(label='Review note', max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 3}))

class EmployerContactForm(forms.Form):
    name = forms.CharField(label='Contact name', max_length=150)
    email = forms.EmailField(label='Contact email', max_length=254)
    phone = forms.CharField(label='Phone (optional)', max_length=40, required=False)
    function = forms.CharField(label='Role in the company (optional)', max_length=150, required=False)

class ImportAssignmentForm(forms.Form):
    adviser = forms.ModelChoiceField(label='Adviser responsible for this offer', queryset=None, required=False, empty_label='Unassigned')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        self.fields['adviser'].queryset = get_user_model().objects.filter(is_active=True, profile__role='adviser', profile__verified=True).select_related('profile').order_by('profile__name', 'pk')
        self.fields['adviser'].label_from_instance = lambda user: user.profile.name or user.username
