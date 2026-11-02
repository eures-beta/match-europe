"""Only explicit availability slots inform timing suggestions."""

DAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
DERIVED = ('day', 'night', 'weekend')


def suggested_conditions(data):
    if data.get('schedule_preference') != 'specific':
        return []
    slots = {day: set(data.get('schedule_' + day, [])) for day in DAYS}
    result = []
    if any(values & {'morning', 'afternoon'} for values in slots.values()):
        result.append('day')
    if any(values & {'evening', 'night'} for values in slots.values()):
        result.append('night')
    if slots['saturday'] or slots['sunday']:
        result.append('weekend')
    return result


def inconsistent_conditions(data):
    if data.get('schedule_preference') != 'specific' or not data.get('schedule_strict'):
        return []
    available = set(suggested_conditions(data))
    return [
        value
        for value in DERIVED
        if value in data.get('working_conditions', []) and value not in available
    ]
