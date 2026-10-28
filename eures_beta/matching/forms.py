from django import forms
from django.utils.translation import gettext_lazy as _


class ReviewForm(forms.Form):
    note = forms.CharField(
        label=_('Review note'),
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
