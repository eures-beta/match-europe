"""Restore the versioned groups and user-administration permissions."""

from django.core.management.base import BaseCommand
from eures_beta.users.permissions import synchronize_permissions


class Command(BaseCommand):
    help = 'Synchronize versioned administration groups and permissions.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')

    def handle(self, *args, **options):
        result = synchronize_permissions(options['database'])
        self.stdout.write(
            'Administration permissions synchronized: '
            + ', '.join(f'{key}={value}' for key, value in result.items())
        )
