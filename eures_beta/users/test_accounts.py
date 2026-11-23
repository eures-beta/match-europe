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
        'label': _('Adviser'),
    },
    'employer': {
        'email': 'employer@demo.example.invalid',
        'kind': User.Kind.EMPLOYER,
        'is_staff': False,
        'is_superuser': False,
        'label': _('Employer'),
    },
    'admin': {
        'email': 'admin@demo.example.invalid',
        'kind': User.Kind.ADVISER,
        'is_staff': True,
        'is_superuser': True,
        'label': _('Super administrator'),
    },
}

PWA_ACCOUNTS = {
    'candidate-pwa': {
        'email': 'compatible@matching-trial.invalid',
        'kind': User.Kind.CANDIDATE,
        'is_staff': False,
        'is_superuser': False,
        'label': _('Candidate (complete profile)'),
    },
    'candidate-pwa-replay': {
        'email': 'unknown@matching-trial.invalid',
        'kind': User.Kind.CANDIDATE,
        'is_staff': False,
        'is_superuser': False,
        'label': _('Candidate (incomplete profile)'),
    },
}


def account_specs():
    return {
        'adviser': ACCOUNTS['adviser'],
        'employer': ACCOUNTS['employer'],
        **PWA_ACCOUNTS,
        'admin': ACCOUNTS['admin'],
    }


def enabled():
    return bool(
        settings.DEMO_ACCOUNTS_ENABLED
        and settings.DJANGO_ENVIRONMENT in ('local', 'preview')
        and not settings.EMAIL_DELIVERY_ENABLED
    )


def context(request):
    return {'test_accounts_enabled': enabled()}


def fictional_database():
    # A production database accidentally labelled as local must not become public.
    return not User.objects.exclude(email__iendswith='.invalid').exists()


def prepared_user(key):
    specification = account_specs().get(key)
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
