from django import forms
from django.utils.translation import gettext_lazy as _


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_('Email address'),
        max_length=254,
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
        from .models import User

        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _('An account already exists for this email address.')
            )
        return email
