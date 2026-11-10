"""Validate pair-specific candidate facts before evaluating a match."""

from django.core.exceptions import ValidationError
from eures_beta.employers.offer_requirements import (
    PERMITS,
    list_of,
    validate_requirements as requirements,
)


def candidate_facts(value):
    if (
        not isinstance(value, dict)
        or set(value) - {'licences_not_held_at_start'}
        or not list_of(value.get('licences_not_held_at_start', []), PERMITS, 6)
    ):
        raise ValidationError('Invalid explicit local candidate facts')
