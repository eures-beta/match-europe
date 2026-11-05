from django.core.management.base import BaseCommand, CommandError
from django.http import Http404
from django.utils import timezone
from eures_beta.candidates.models import CandidateRegistration
from eures_beta.candidates.registration import require_trial


class Command(BaseCommand):
    help = 'Count expired fictional confirmation requests; --apply deletes them.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            require_trial()
        except Http404:
            raise CommandError(
                'Only enabled local/preview trials support this cleanup.'
            ) from None
        queryset = CandidateRegistration.objects.filter(expires_at__lte=timezone.now())
        count = queryset.count()
        if options['apply']:
            queryset.delete()
        self.stdout.write(f'Expired requests: {count}; applied: {options["apply"]}')
