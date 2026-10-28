from django import forms
from django.utils.translation import gettext_lazy as _


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
