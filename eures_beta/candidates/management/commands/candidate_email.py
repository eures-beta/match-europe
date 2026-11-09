"""Private operator simulation; never expose verification links in public pages."""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from eures_beta.candidates.pending import latest_for_email
from eures_beta.candidates.registration import confirmation_message


class Command(BaseCommand):
    help = 'Print a private candidate confirmation email; never sends email.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--origin', required=True)

    def handle(self, *args, **options):
        try:
            pending = latest_for_email(options['email'])
            if pending is None:
                raise ValidationError('No request.')
            subject, body = confirmation_message(pending, options['origin'])
        except ValidationError:
            raise CommandError('No valid request or allowed origin.') from None
        self.stdout.write(subject + '\n\n' + body)
