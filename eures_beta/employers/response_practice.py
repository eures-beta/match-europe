"""Declared response practices, stored per employer account; no automatic reminder policy."""

from django import forms
from django.utils.translation import gettext_lazy as _

RESPONSE_COVERAGE = [
    ('all', _('Yes, all applications')),
    ('selected', _('No, only applicants selected for the next recruitment stage')),
    ('varies', _('It depends on the recruitment')),
]
RESPONSE_TIME = [
    ('under_week', _('Less than one week')),
    ('one_two_weeks', _('Between 1 and 2 weeks')),
    ('two_weeks_month', _('More than 2 weeks and up to 1 month')),
    ('over_month', _('More than one month')),
    ('variable', _('The timeframe varies too much to estimate')),
]


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
