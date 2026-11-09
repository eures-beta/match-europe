from django.core.management.base import BaseCommand
from eures_beta.candidates.pending import expired


class Command(BaseCommand):
    help = 'Count expired confirmation requests; --apply deletes them.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        queryset = expired()
        count = queryset.count()
        if options['apply']:
            queryset.delete()
        self.stdout.write(f'Expired requests: {count}; applied: {options["apply"]}')
