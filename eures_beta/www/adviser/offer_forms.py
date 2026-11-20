"""Explicit establishment selection and telephone confirmation."""

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from eures_beta.employers.models import Company, CompanyMembership
from eures_beta.users.models import User


class DepositSetupForm(forms.Form):
    company = forms.ModelChoiceField(
        label=_('Existing establishment'),
        queryset=Company.objects.order_by('name', 'pk'),
        required=False,
        empty_label=_('Create a separate establishment'),
    )
    company_name = forms.CharField(
        label=_('New establishment name'), max_length=100, required=False
    )
    employer = forms.ModelChoiceField(
        label=_('Employer account (optional)'),
        queryset=User.objects.filter(kind='employer', is_active=True).order_by('email'),
        required=False,
        help_text=_(
            'For an existing establishment, select one of its active members. For a new establishment, the selected account will have access to its offers. Leave blank if the employer has no account.'
        ),
    )

    def clean(self):
        values = super().clean()
        company, employer = values.get('company'), values.get('employer')
        if not company and not values.get('company_name'):
            self.add_error(
                'company_name',
                _(
                    'Enter the new establishment name or select an existing establishment.'
                ),
            )
        if (
            company
            and employer
            and not CompanyMembership.objects.filter(
                company=company, user=employer, active=True
            ).exists()
        ):
            self.add_error(
                'employer',
                _(
                    'This account is not an active member of the selected establishment.'
                ),
            )
        if (
            company
            and not employer
            and CompanyMembership.objects.filter(
                company=company,
                active=True,
                user__is_active=True,
                user__kind='employer',
            ).exists()
        ):
            self.add_error(
                'employer',
                _('Select the employer contact account for this establishment.'),
            )
        return values


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
