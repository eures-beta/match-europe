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


class EmployerInvitationForm(LoginForm):
    language = forms.ChoiceField(
        label=_('Invitation language'),
        choices=(('fr', 'Français'), ('en', 'English'), ('de', 'Deutsch')),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _('An account already exists for this email address.')
            )
        return email


class AdviserSignatureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'adviser_organisation')
        labels = {
            'first_name': pgettext_lazy('adviser signature', 'First name'),
            'last_name': pgettext_lazy('adviser signature', 'Last name'),
            'adviser_organisation': pgettext_lazy('adviser signature', 'Organisation'),
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'adviser_organisation': forms.TextInput(
                attrs={'autocomplete': 'organization'}
            ),
        }
