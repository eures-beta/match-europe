"""Minimal first-establishment form; names never establish membership."""
from django import forms
from django.utils.translation import gettext_lazy as _


class EstablishmentForm(forms.Form):
    name = forms.CharField(label=_("Establishment name"), max_length=100,
                          widget=forms.TextInput(attrs={'autocomplete': 'organization'}))
