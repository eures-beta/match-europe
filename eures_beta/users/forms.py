from django import forms
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_('Email address'),
        max_length=254,
        error_messages={'invalid': _('Enter a valid email address.')},
        widget=forms.EmailInput(
            attrs={'autocomplete': 'email', 'autocapitalize': 'none'}
        ),
    )


class AdviserSignatureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'organization_name')
        labels = {
            'first_name': pgettext_lazy('adviser signature', 'First name'),
            'last_name': pgettext_lazy('adviser signature', 'Last name'),
            'organization_name': pgettext_lazy('adviser signature', 'Organisation'),
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'organization_name': forms.TextInput(
                attrs={'autocomplete': 'organization'}
            ),
        }
