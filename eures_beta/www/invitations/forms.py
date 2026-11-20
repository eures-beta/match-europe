from django import forms
from django.utils.translation import gettext_lazy as _
from eures_beta.www.accounts.forms import LoginForm
from eures_beta.users.models import User
from eures_beta.employers.models import Company


class InvitationForm(LoginForm):
    company = forms.ModelChoiceField(
        label=_('Establishment access (optional)'),
        queryset=Company.objects.order_by('name', 'pk'),
        required=False,
        help_text=_(
            'The invited employer will have access to all offers of this establishment after accepting the invitation.'
        ),
    )
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


class RecipientForm(forms.Form):
    email = forms.EmailField(label='Adresse e-mail')
    first_name = forms.CharField(label='Prénom', max_length=150, required=False)
    last_name = forms.CharField(label='Nom', max_length=150, required=False)

    def clean_email(self):
        return self.cleaned_data['email'].lower()
