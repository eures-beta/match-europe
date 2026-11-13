"""Employer response practice form; choices live with the domain model."""

from django import forms
from django.utils.translation import gettext_lazy as _
from eures_beta.employers.response_practice import RESPONSE_COVERAGE, RESPONSE_TIME


class ResponsePracticeForm(forms.Form):
    response_coverage = forms.ChoiceField(
        label=_('Do you reply to all applications received?'),
        help_text=_('Do not count automatic acknowledgements.'),
        choices=[('', _('Please choose'))] + RESPONSE_COVERAGE,
        required=True,
    )
    response_time = forms.ChoiceField(
        label=_('How long do you usually take to send a first reply?'),
        help_text=_(
            'Count from receipt of the application, excluding automatic acknowledgements. '
            'If you do not reply to everyone, indicate the timeframe for the people you contact.'
        ),
        choices=[('', _('Please choose'))] + RESPONSE_TIME,
        required=True,
    )
