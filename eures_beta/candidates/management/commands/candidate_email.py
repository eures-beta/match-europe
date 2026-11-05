"""Private operator simulation; never expose verification links in public pages."""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.http import Http404
from eures_beta.candidates.models import CandidateRegistration
from eures_beta.candidates.registration import simulated_email


class Command(BaseCommand):
    help = 'Print a private fictional candidate confirmation email; never sends email.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--origin', required=True)

    def handle(self, *args, **options):
        try:
            pending = CandidateRegistration.objects.get(
                email__iexact=options['email'].strip()
            )
            subject, body = simulated_email(pending, options['origin'])
        except (CandidateRegistration.DoesNotExist, ValidationError, Http404):
            raise CommandError('No valid trial request or allowed origin.') from None
        self.stdout.write(subject + '\n\n' + body)
