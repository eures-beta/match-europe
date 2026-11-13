from django import forms
from django.utils.translation import gettext_lazy as _


class EmployerContactForm(forms.Form):
    name = forms.CharField(label=_('Contact name'), max_length=150)
    email = forms.EmailField(label=_('Contact email'), max_length=254)
    phone = forms.CharField(label=_('Phone (optional)'), max_length=40, required=False)
    function = forms.CharField(
        label=_('Role in the company (optional)'), max_length=150, required=False
    )
