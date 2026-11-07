"""Deterministic local experiment. No ORM, inference, messaging or side effects."""

from datetime import date
from decimal import Decimal, InvalidOperation

VERSION = 'local-evidence-v1'
# Experimental point budget only: neither calibrated nor used for rejection/ranking.
WEIGHTS = {
    'skills': 40,
    'languages': 20,
    'mobility': 15,
    'conditions': 15,
    'salary': 10,
}
LEVELS = ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')
DAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
PERIODS = ('morning', 'afternoon', 'evening', 'night')


def skill_set(value):
    return {
        uri
        for selection in (value or {}).values()
        for uri in selection.get('skills', [])
    }


def iso_date(value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def evaluate(candidate, offer, requirements=None, facts=None, *, today):
    """Use explicit structured declarations only; blank/unchecked is never a refusal.

    requirements/facts are local supplements, not inferred from free text.
    All required schedule slots mean mandatory attendance, not alternative shifts.
    """
    requirements, facts = requirements or {}, facts or {}
    rows = []

    def add(
        key,
        dimension,
        state='unknown',
        reason='missing',
        *,
        blocking=False,
        reference='',
        expected='',
        declared='',
    ):
        rows.append(
            dict(
                key=key,
                dimension=dimension,
                state=state,
                reason=reason,
                blocking=blocking,
                reference=reference,
                expected=expected,
                declared=declared,
            )
        )

    selections = offer.get('occupationSkills') or {}
    expected = skill_set(selections)
    acquired = set(candidate.get('acquired_skills') or []) | skill_set(
        candidate.get('occupation_skills')
    )
    learning = set(candidate.get('learning_activities') or [])
    if not expected:
        add('skills', 'skills')
    else:
        for uri in sorted(expected):
            # Several occupations can represent alternatives: do not merge requirements.
            if len(selections) > 1:
                add('skill', 'skills', reason='alternative_occupations', reference=uri)
            elif uri in acquired:
                add('skill', 'skills', 'match', 'declared', reference=uri)
            else:
                add(
                    'skill',
                    'skills',
                    reason='learning' if uri in learning else 'not_declared',
                    reference=uri,
                )

    expected_languages = requirements.get('languages')
    actual_languages = {
        x['code']: x['level']
        for x in candidate.get('language_skills', {}).get('languages', [])
    }
    if expected_languages == []:
        add('languages', 'languages', 'not_applicable', 'no_requirement')
    elif not expected_languages:
        add('languages', 'languages')
    else:
        for item in expected_languages:
            code, level = item['code'], item['level']
            actual = actual_languages.get(code)
            state = (
                'unknown'
                if actual not in LEVELS
                else (
                    'match'
                    if LEVELS.index(actual) >= LEVELS.index(level)
                    else 'mismatch'
                )
            )
            add(
                'language',
                'languages',
                state,
                'language_level',
                reference=code,
                expected=level,
                declared=actual or '',
            )

    country = requirements.get('country')
    if country and country in candidate.get('desired_countries', []):
        add('mobility', 'mobility', 'match', 'country_preference', reference=country)
    else:
        add('mobility', 'mobility', reason='country_unconfirmed')

    deadline = iso_date(requirements.get('latest_start'))
    start = (
        iso_date(candidate.get('available_from'))
        if candidate.get('availability') == 'date'
        else (today if candidate.get('availability') == 'now' else None)
    )
    if deadline and start:
        conflict = start > deadline
        add(
            'availability',
            'conditions',
            'mismatch' if conflict else 'match',
            'start_date',
            blocking=conflict and requirements.get('start_mandatory') is True,
            expected=str(deadline),
            declared=str(start),
        )
    else:
        add('availability', 'conditions', reason='date_unconfirmed')

    required_slots = set(requirements.get('schedule') or [])
    declared_slots = {
        day + ':' + slot
        for day in DAYS
        for slot in candidate.get('schedule_' + day, [])
    }
    if required_slots and candidate.get('schedule_preference') == 'specific':
        if required_slots <= declared_slots:
            add(
                'schedule',
                'conditions',
                'match',
                'schedule',
                expected=','.join(sorted(required_slots)),
                declared=','.join(sorted(declared_slots)),
            )
        elif candidate.get('schedule_strict') is True:
            add(
                'schedule',
                'conditions',
                'mismatch',
                'schedule',
                blocking=requirements.get('schedule_mandatory') is True,
                expected=','.join(sorted(required_slots)),
                declared=','.join(sorted(declared_slots)),
            )
        else:
            add('schedule', 'conditions', reason='schedule_unconfirmed')
    else:
        add('schedule', 'conditions', reason='schedule_unconfirmed')

    employer_permits = offer.get('requirements', {})
    permits = set(employer_permits.get('permits') or [])
    held = set(candidate.get('licences_held') or [])
    absent = set(facts.get('licences_not_held_at_start') or []) - held
    if employer_permits.get('permitRequired') == 'no' and not permits:
        add('permits', 'conditions', 'not_applicable', 'no_requirement')
    elif employer_permits.get('permitRequired') == 'yes' and permits:
        for permit in sorted(permits):
            if permit == 'other':
                add('permit', 'conditions', reason='other_permit', reference=permit)
            elif permit in held:
                add('permit', 'conditions', 'match', 'declared', reference=permit)
            elif permit in absent:
                add(
                    'permit',
                    'conditions',
                    'mismatch',
                    'explicit_absence',
                    blocking=permit in requirements.get('mandatory_permits', []),
                    reference=permit,
                )
            else:
                add('permit', 'conditions', reason='not_declared', reference=permit)
    else:
        add('permits', 'conditions')

    expected_conditions = set(employer_permits.get('workConditions') or []) - {
        'unknown',
        'none',
    }
    accepted_conditions = set(candidate.get('working_conditions') or []) - {
        'discuss',
        'none',
    }
    if employer_permits.get('workConditions') == ['none']:
        add('work_conditions', 'conditions', 'not_applicable', 'no_requirement')
    elif expected_conditions:
        for condition in sorted(expected_conditions):
            add(
                'work_condition',
                'conditions',
                'match' if condition in accepted_conditions else 'unknown',
                'declared' if condition in accepted_conditions else 'not_declared',
                reference=condition,
            )
    else:
        add('work_conditions', 'conditions')

    contracts = {
        'PERMANENT_CONTRACT': 'permanent',
        'FIXED_TERM_CONTRACT': 'fixed',
        'TEMPORARY_WORK': 'temporary',
        'APPRENTICESHIP': 'apprenticeship',
    }
    contract = contracts.get(offer.get('contractType'))
    if contract and contract in candidate.get('contract_types', []):
        add('contract', 'conditions', 'match', 'declared', reference=contract)
    else:
        add('contract', 'conditions', reason='contract_unconfirmed')

    salary = requirements.get('salary') or {}
    minimum = number(candidate.get('salary_amount'))
    maximum = number(salary.get('maximum'))
    comparable = (
        candidate.get('salary_preference') == 'minimum'
        and minimum is not None
        and maximum is not None
        and all(
            candidate.get('salary_' + key) == salary.get(key) and salary.get(key)
            for key in ('currency', 'period', 'basis')
        )
        # Monthly/yearly amounts need an explicit common working-hours basis.
        and salary.get('period') == 'hour'
    )
    if comparable:
        add(
            'salary',
            'salary',
            'match' if minimum <= maximum else 'mismatch',
            'salary_comparison',
            expected=str(maximum),
            declared=str(minimum),
            reference=salary['currency'],
        )
    else:
        add('salary', 'salary', reason='salary_unconfirmed')

    dimensions = []
    for dimension, weight in WEIGHTS.items():
        group = [row for row in rows if row['dimension'] == dimension]
        active = [row for row in group if row['state'] != 'not_applicable']
        # A missing or inapplicable item never earns points. No renormalisation.
        unit = Decimal(weight) / len(group)
        low = sum((unit for row in group if row['state'] == 'match'), Decimal(0))
        unknown = sum((unit for row in group if row['state'] == 'unknown'), Decimal(0))
        dimensions.append(
            dict(
                key=dimension,
                weight=weight,
                established=float(round(low, 2)),
                unresolved=float(round(unknown, 2)),
                evaluated=sum(row['state'] in ('match', 'mismatch') for row in active),
                applicable=len(active),
            )
        )
    established = round(sum(x['established'] for x in dimensions), 2)
    unresolved = round(sum(x['unresolved'] for x in dimensions), 2)
    blocked = any(row['blocking'] for row in rows)
    matched = sum(row['state'] == 'match' for row in rows)
    return dict(
        version=VERSION,
        experimental=True,
        rows=rows,
        dimensions=dimensions,
        established=established,
        unresolved=unresolved,
        blocked=blocked,
        matched=matched,
        status='blocked' if blocked else ('review' if matched else 'insufficient'),
        # These question codes are for later conversation tooling; no messages sent.
        questions=[
            dict(key=row['key'], reference=row['reference'], reason=row['reason'])
            for row in rows
            if row['state'] == 'unknown'
        ],
    )
