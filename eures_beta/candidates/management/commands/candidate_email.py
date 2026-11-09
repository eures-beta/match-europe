"""Private operator simulation; never expose verification links in public pages."""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from eures_beta.users.models import User
from eures_beta.candidates.registration import confirmation_message


class Command(BaseCommand):
    help = 'Print a private candidate confirmation email; never sends email.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--origin', required=True)

    def handle(self, *args, **options):
        try:
            pending = User.objects.get(email__iexact=options['email'].strip())
            subject, body = confirmation_message(pending, options['origin'])
        except (User.DoesNotExist, ValidationError):
            raise CommandError('No valid request or allowed origin.') from None
        self.stdout.write(subject + '\n\n' + body)
