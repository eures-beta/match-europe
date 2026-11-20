"""Validate the role of explicitly named user relations before ordinary saves."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_user_roles(instance, **fields):
    messages = {
        'adviser': _('An adviser account is required.'),
        'employer': _('An employer account is required.'),
    }
    for field, kind in fields.items():
        if getattr(instance, field + '_id') is not None:
            if getattr(instance, field).kind != kind:
                raise ValidationError({field: messages[kind]})
