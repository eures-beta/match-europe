"""Shared validation of structured job offers."""

from .offer_ingestion import ImportFailure, empty_data

CONTRACTS = {
    'PERMANENT_CONTRACT',
    'FIXED_TERM_CONTRACT',
    'TEMPORARY_WORK',
    'INTERNSHIP',
    'APPRENTICESHIP',
    'FREELANCE',
    'TRAINING',
}


def clean_data(raw):
    if not isinstance(raw, dict):
        raise ImportFailure('invalid_data')
    out = empty_data()
    for key, limit in {
        'title': 125,
        'companyName': 100,
        'city': 150,
        'contractType': 32,
        'description': 16000,
        'desiredProfile': 4000,
    }.items():
        value = raw.get(key, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ImportFailure('invalid_data')
        out[key] = value.strip()
    if out['contractType'] and out['contractType'] not in CONTRACTS:
        raise ImportFailure('invalid_data')
    if 'occupation' in raw:
        from .occupation_selection import clean_selection

        try:
            out['occupation'] = clean_selection(raw['occupation'], out['title'])
        except ValueError:
            raise ImportFailure('invalid_data') from None
    clar = raw.get('clarifications', {})
    if 'occupationSkills' in raw:
        from eures_beta.skills.continuous import validated_selection

        try:
            out['occupationSkills'] = validated_selection(
                raw['occupationSkills'], out.get('occupation', {}).get('uris', [])
            )
        except ValueError:
            raise ImportFailure('invalid_data') from None
    if not isinstance(clar, dict):
        raise ImportFailure('invalid_data')
    for key in out['clarifications']:
        value = clar.get(key, '')
        if not isinstance(value, str) or len(value) > 1000:
            raise ImportFailure('invalid_data')
        out['clarifications'][key] = value.strip()
    req = raw.get('requirements', {})
    if not isinstance(req, dict):
        raise ImportFailure('invalid_data')
    allowed = {
        'workConditions': {
            'early',
            'night',
            'weekend',
            'variable',
            'shift',
            'physical',
            'standing',
            'split',
            'outdoor',
            'travel',
            'none',
            'unknown',
        },
        'permits': {'B', 'C', 'CE', 'D', 'DE', 'CACES', 'other'},
        'arrivalAids': {
            'housing',
            'admin',
            'transport',
            'onboarding',
            'other',
            'none',
            'unknown',
        },
    }
    for key, options in allowed.items():
        values = req.get(key, [])
        if (
            not isinstance(values, list)
            or len(values) > len(options)
            or any(not isinstance(v, str) or v not in options for v in values)
        ):
            raise ImportFailure('invalid_data')
        if (
            key != 'permits'
            and any(v in values for v in ('none', 'unknown'))
            and len(values) > 1
        ):
            raise ImportFailure('invalid_data')
        out['requirements'][key] = list(dict.fromkeys(values))
    value = req.get('permitRequired', '')
    if value not in ('', 'yes', 'no'):
        raise ImportFailure('invalid_data')
    out['requirements']['permitRequired'] = value
    for key in ('permitOther', 'aidOther'):
        value = req.get(key, '')
        if not isinstance(value, str) or len(value) > 500:
            raise ImportFailure('invalid_data')
        out['requirements'][key] = value.strip()
    if out['requirements']['permitRequired'] != 'yes':
        out['requirements']['permits'] = []
        out['requirements']['permitOther'] = ''
    if 'other' not in out['requirements']['permits']:
        out['requirements']['permitOther'] = ''
    if 'other' not in out['requirements']['arrivalAids']:
        out['requirements']['aidOther'] = ''
    for key in ('crossBorder', 'relocation'):
        value = raw.get(key, '')
        if value not in ('', 'yes', 'no', 'discuss'):
            raise ImportFailure('invalid_data')
        out[key] = value
    questions = raw.get('questions', [])
    if not isinstance(questions, list) or len(questions) > 20:
        raise ImportFailure('invalid_data')
    for q in questions:
        if (
            not isinstance(q, dict)
            or not isinstance(q.get('question'), str)
            or not 1 <= len(q['question'].strip()) <= 2000
            or type(q.get('mandatory')) is not bool
        ):
            raise ImportFailure('invalid_data')
        out['questions'].append(
            {
                'question': q['question'].strip(),
                'mandatory': q['mandatory'],
                'humanReviewRequired': True,
            }
        )
    return out
