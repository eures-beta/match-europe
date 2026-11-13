"""Operator-only simulation for an existing active account; no user creation."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import override, gettext
from sesame.utils import get_query_string
from eures_beta.emails.origins import validate_origin
from eures_beta.users.models import User


class Command(BaseCommand):
    help = 'Print a private simulated sign-in email for an existing account; contains a secret one-hour link.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--origin', default=settings.LOGIN_EMAIL_ORIGIN)
        parser.add_argument('--language', choices=('fr', 'en', 'de'), default='fr')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(
                email__iexact=options['email'].strip(), is_active=True
            )
            origin = validate_origin(options['origin'])
        except (User.DoesNotExist, ValidationError) as error:
            raise CommandError(
                'An existing active account and an allowed origin are required.'
            ) from error
        link = origin + reverse('magic_confirm') + get_query_string(user)
        with override(options['language']):
            subject = gettext('Your Match Europe sign-in link')
            body = render_to_string('users/login_email.txt', {'link': link})
        self.stdout.write(subject + '\n\n' + body)
