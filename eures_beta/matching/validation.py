"""Validate the bounded local supplements before they can affect an evaluation."""

from django.core.exceptions import ValidationError
from eures_beta.candidates.language_choices import LANGUAGE_CODES
from .engine import DAYS, PERIODS, LEVELS, iso_date, number

PERMITS = {'B', 'C', 'CE', 'D', 'DE', 'CACES'}


def list_of(value, allowed, maximum):
    return (
        isinstance(value, list)
        and len(value) <= maximum
        and all(isinstance(item, str) and item in allowed for item in value)
        and len(value) == len(set(value))
    )


def requirements(value):
    invalid = ValidationError('Invalid structured local requirements')
    if not isinstance(value, dict) or set(value) - {
        'country',
        'languages',
        'latest_start',
        'start_mandatory',
        'schedule',
        'schedule_mandatory',
        'mandatory_permits',
        'salary',
    }:
        raise invalid
    if 'country' in value and value['country'] not in ('FR', 'LU', 'DE', 'BE'):
        raise invalid
    for key in ('start_mandatory', 'schedule_mandatory'):
        if key in value and type(value[key]) is not bool:
            raise invalid
    if 'latest_start' in value and not iso_date(value['latest_start']):
        raise invalid
    if value.get('start_mandatory') and not value.get('latest_start'):
        raise invalid
    slots = {day + ':' + period for day in DAYS for period in PERIODS}
    if 'schedule' in value and not list_of(value['schedule'], slots, 28):
        raise invalid
    if value.get('schedule_mandatory') and not value.get('schedule'):
        raise invalid
    if 'mandatory_permits' in value and not list_of(
        value['mandatory_permits'], PERMITS, 6
    ):
        raise invalid
    if 'languages' in value:
        rows = value['languages']
        if not isinstance(rows, list) or len(rows) > 20:
            raise invalid
        seen = set()
        for row in rows:
            if (
                not isinstance(row, dict)
                or set(row) != {'code', 'level'}
                or not isinstance(row['code'], str)
                or row['code'] not in LANGUAGE_CODES
                or not isinstance(row['level'], str)
                or row['level'] not in LEVELS
                or row['code'] in seen
            ):
                raise invalid
            seen.add(row['code'])
    if 'salary' in value:
        salary = value['salary']
        if (
            not isinstance(salary, dict)
            or set(salary) != {'maximum', 'currency', 'period', 'basis'}
            or number(salary.get('maximum')) is None
            or number(salary['maximum']) > 10000000
            or salary['currency'] not in ('EUR', 'GBP', 'CHF')
            or salary['period'] not in ('hour', 'month', 'year')
            or salary['basis'] not in ('gross', 'net')
        ):
            raise invalid


def candidate_facts(value):
    if (
        not isinstance(value, dict)
        or set(value) - {'licences_not_held_at_start'}
        or not list_of(value.get('licences_not_held_at_start', []), PERMITS, 6)
    ):
        raise ValidationError('Invalid explicit local candidate facts')
