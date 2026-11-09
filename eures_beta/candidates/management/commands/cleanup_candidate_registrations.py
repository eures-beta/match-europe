from django.core.management.base import BaseCommand
from django.utils import timezone
from eures_beta.users.models import User


class Command(BaseCommand):
    help = 'Count expired confirmation requests; --apply deletes them.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        queryset = User.objects.filter(
            kind='candidate',
            is_active=False,
            candidate_verification_nonce__isnull=False,
            candidate_verification_expires__lte=timezone.now(),
        )
        count = queryset.count()
        if options['apply']:
            queryset.delete()
        self.stdout.write(f'Expired requests: {count}; applied: {options["apply"]}')
