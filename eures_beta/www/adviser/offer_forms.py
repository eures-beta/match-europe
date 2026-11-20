"""Explicit establishment selection and telephone confirmation."""

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DepositSetupForm(forms.Form):
    email = forms.EmailField(label=_('Employer email'), max_length=254)

    def clean_email(self):
        from eures_beta.employers.adviser_deposit import check_employer

        email = self.cleaned_data['email'].strip().lower()
        check_employer(email)
        return email


class PhoneConfirmationForm(forms.Form):
    phone_confirmed = forms.BooleanField(
        label=_('The employer confirmed this offer to me by telephone.')
    )
    confirmed_on = forms.DateField(
        label=_('Date of the telephone confirmation'),
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        initial=timezone.localdate,
    )

    def clean_confirmed_on(self):
        date = self.cleaned_data['confirmed_on']
        if date > timezone.localdate():
            raise forms.ValidationError(
                _('Enter the date of the telephone confirmation, no later than today.')
            )
        return date
