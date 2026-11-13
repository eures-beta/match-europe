"""Idempotent, opt-in fictional data; never resets a database."""

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from eures_beta.users.models import User
from eures_beta.users.test_accounts import (
    ACCOUNTS,
    PWA_ACCOUNTS,
    enabled,
    fictional_database,
    prepared_user,
)


class Command(BaseCommand):
    help = 'Add the fictional local/preview accounts and two offers, preserving existing test data.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not enabled() or not fictional_database():
            raise CommandError(
                'Test seeding requires an explicitly enabled local/preview database with only .invalid accounts.'
            )
        from eures_beta.matching.access import test_data_enabled

        seed_pwa = settings.DJANGO_ENVIRONMENT == 'preview' and test_data_enabled()
        accounts = {**ACCOUNTS, **PWA_ACCOUNTS} if seed_pwa else ACCOUNTS
        for key, specification in accounts.items():
            if (
                User.objects.filter(email__iexact=specification['email']).exists()
                and prepared_user(key) is None
            ):
                raise CommandError(
                    'A fixture account has unexpected attributes; no data changed.'
                )
        users = {}
        for key, specification in accounts.items():
            user = prepared_user(key)
            if user is None:
                user = User.objects.create_user(
                    **{
                        field: value
                        for field, value in specification.items()
                        if field != 'label'
                    }
                )
            users[key] = user
        from eures_beta.employers.test_data import seed_test_offers

        seed_test_offers(users['employer'])
        call_command('sync_group_and_perms', stdout=self.stdout)
        if seed_pwa:
            call_command('seed_matching_trial', stdout=self.stdout)
        self.stdout.write(
            'Fictional test accounts and offers are ready; existing data preserved.'
        )
