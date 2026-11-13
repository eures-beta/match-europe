"""Invitation role and historical versioned permission policy."""

EMPLOYER_INVITER_GROUP = 'employer-inviters'


def can_invite(user):
    return bool(user.is_authenticated and user.is_active and user.kind == 'adviser')


def get_group_permissions():
    from .models import Invitation

    return {EMPLOYER_INVITER_GROUP: {Invitation: {'add', 'view'}}}
