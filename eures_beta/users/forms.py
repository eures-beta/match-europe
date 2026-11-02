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
