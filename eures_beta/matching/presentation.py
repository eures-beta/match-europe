from django.utils.translation import gettext_lazy as _, get_language_info
from eures_beta.candidates.forms import (
    ConditionsForm,
    SCHEDULE_DAYS,
    SCHEDULE_PERIODS,
)
from eures_beta.skills.skills_pilot import catalogue

DIMENSIONS = {
    'skills': _('Declared skills'),
    'languages': _('Languages'),
    'mobility': _('Mobility'),
    'conditions': _('Availability and conditions'),
    'salary': _('Salary'),
}
STATES = {
    'match': _('Established correspondence'),
    'unknown': _('To verify'),
    'mismatch': _('Explicit incompatibility'),
    'not_applicable': _('No requirement'),
}
STATUSES = {
    'blocked': _('Blocked for this offer'),
    'review': _('Possible correspondence — human review needed'),
    'insufficient': _('More information needed'),
}
DECISIONS = {
    'pending': _('Not reviewed'),
    'retained': _('Retained for review'),
    'refused': _('Refused by the local operator'),
}
KEYS = {
    'skills': _('Declared skills'),
    'skill': _('Declared skill'),
    'languages': _('Languages'),
    'language': _('Language level'),
    'mobility': _('Country preference'),
    'availability': _('Start date'),
    'schedule': _('Required time slots'),
    'permits': _('Driving licences and authorisations'),
    'permit': _('Required authorisation'),
    'work_conditions': _('Working conditions'),
    'work_condition': _('Working condition'),
    'contract': _('Contract'),
    'salary': _('Salary'),
}
REASONS = {
    'missing': _('Comparable information is missing.'),
    'declared': _('Based on explicit declarations, not certification.'),
    'alternative_occupations': _(
        'Several occupations are selected: clarify which skills apply to this position.'
    ),
    'learning': _(
        'The candidate wants to learn this activity; mastery is not confirmed.'
    ),
    'not_declared': _('Not declared does not mean absent. Ask the candidate.'),
    'no_requirement': _(
        'The employer explicitly declares no requirement on this point.'
    ),
    'language_level': _('Declared level compared with the explicitly required level.'),
    'country_preference': _(
        'The country is among the candidate’s choices. The journey still needs checking.'
    ),
    'country_unconfirmed': _(
        'Confirm the workplace and the candidate’s interest in this location.'
    ),
    'start_date': _('Confirmed availability compared with the latest start date.'),
    'date_unconfirmed': _('Clarify the start date and whether it is mandatory.'),
    'schedule': _(
        'Required attendance compared with the candidate’s declared time slots.'
    ),
    'schedule_unconfirmed': _(
        'Confirm exact attendance times and whether they are mandatory.'
    ),
    'other_permit': _(
        'The generic “other” authorisation cannot establish compatibility.'
    ),
    'explicit_absence': _(
        'The candidate explicitly declared not holding this authorisation at the required start date.'
    ),
    'contract_unconfirmed': _(
        'Confirm interest in this contract. An unchecked choice is not a refusal.'
    ),
    'salary_comparison': _(
        'Hourly amounts compared in the same currency and gross/net basis.'
    ),
    'salary_unconfirmed': _(
        'Confirm comparable pay amounts, currency, gross/net basis and working hours.'
    ),
}


def present(result, language):
    cards, skills = catalogue()
    conditions = dict(ConditionsForm.base_fields['working_conditions'].choices)
    contracts = dict(ConditionsForm.base_fields['contract_types'].choices)
    days, periods = dict(SCHEDULE_DAYS), dict(SCHEDULE_PERIODS)
    countries = {
        'FR': _('France'),
        'DE': _('Germany'),
        'BE': _('Belgium'),
        'LU': _('Luxembourg'),
    }

    def slots(value):
        result = []
        for slot in value.split(',') if value else []:
            day, period = slot.split(':')
            result.append(str(days[day]) + ' — ' + str(periods[period]))
        return ', '.join(result)

    rows = []
    for row in result['rows']:
        reference = row['reference']
        if row['key'] == 'skill':
            reference = skills.get(reference, {}).get('labels', {}).get(language, '')
        if row['key'] == 'language':
            reference = get_language_info(reference)['name_translated']
        elif row['key'] == 'work_condition':
            reference = conditions.get(reference, '')
        elif row['key'] == 'contract':
            reference = contracts.get(reference, '')
        elif row['key'] == 'mobility':
            reference = countries.get(reference, '')
        expected, declared = row.get('expected', ''), row.get('declared', '')
        if row['key'] == 'schedule':
            expected, declared = slots(expected), slots(declared)
        rows.append(
            {
                **row,
                'label': KEYS[row['key']],
                'reference_label': reference,
                'expected_label': expected,
                'declared_label': declared,
                'state_label': STATES[row['state']],
                'explanation': REASONS[row['reason']],
            }
        )
    return {
        **result,
        'rows': rows,
        'strengths': [row for row in rows if row['state'] == 'match'],
        'incompatibilities': [row for row in rows if row['state'] == 'mismatch'],
        'unknowns': [row for row in rows if row['state'] == 'unknown'],
        'status_label': STATUSES[result['status']],
        'dimensions': [
            {**d, 'label': DIMENSIONS[d['key']]} for d in result['dimensions']
        ],
    }
