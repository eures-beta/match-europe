"""Explicit operator-only email simulation; never called from HTTP views or logs."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from eures_beta.invitations.services import invitation_message
from eures_beta.invitations.models import Invitation


class Command(BaseCommand):
    help = 'Print one private simulated invitation email. Contains a one-use sign-in link; do not log or share.'

    def add_arguments(self, parser):
        parser.add_argument('invitation_id')
        parser.add_argument('--origin', default=settings.LOGIN_EMAIL_ORIGIN)

    def handle(self, *args, **options):
        try:
            invitation = Invitation.objects.get(pk=options['invitation_id'])
            subject, body = invitation_message(invitation, options['origin'])
        except (Invitation.DoesNotExist, ValidationError, ValueError) as error:
            raise CommandError(
                'Cannot simulate this invitation; check its ID, validity and origin.'
            ) from error
        self.stdout.write(subject + '\n\n' + body)
