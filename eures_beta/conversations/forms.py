from django import forms
from django.utils.translation import gettext_lazy as _


class MessageForm(forms.Form):
    body = forms.CharField(
        label=_('Your message'),
        max_length=4000,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
