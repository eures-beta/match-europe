"""Declared response practices, stored per employer account; no automatic reminder policy."""

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
