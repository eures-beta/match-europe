"""Explicit fictional accounts; isolated from production."""

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import User

ACCOUNTS = {
    'adviser': {
        'email': 'adviser@demo.example.invalid',
        'kind': User.Kind.ADVISER,
        'is_staff': False,
        'is_superuser': False,
        'label': _('Test adviser'),
    },
    'employer': {
        'email': 'employer@demo.example.invalid',
        'kind': User.Kind.EMPLOYER,
        'is_staff': False,
        'is_superuser': False,
        'label': _('Test employer'),
    },
    'admin': {
        'email': 'admin@demo.example.invalid',
        'kind': User.Kind.ADVISER,
        'is_staff': True,
        'is_superuser': True,
        'label': _('Test superadministrator'),
    },
}


def enabled():
    return bool(
        settings.TEST_ACCOUNTS_ENABLED
        and settings.DJANGO_ENVIRONMENT in ('local', 'preview')
        and not settings.EMAIL_DELIVERY_ENABLED
    )


def context(request):
    return {'test_accounts_enabled': enabled()}


def fictional_database():
    # A production database accidentally labelled as local must not become public.
    return not User.objects.exclude(email__iendswith='.invalid').exists()


def prepared_user(key):
    specification = ACCOUNTS.get(key)
    if not specification:
        return None
    user = User.objects.filter(email__iexact=specification['email']).first()
    if not user or not user.is_active or user.has_usable_password():
        return None
    if any(
        getattr(user, field) != specification[field]
        for field in ('kind', 'is_staff', 'is_superuser')
    ):
        return None
    return user
