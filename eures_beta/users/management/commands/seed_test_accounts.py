"""Idempotent, opt-in fictional data; never resets a database."""

from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from eures_beta.introductions import offer_review_services
from eures_beta.introductions.models import CandidateOfferReview
from eures_beta.matching.models import CandidateOfferMatch
from eures_beta.users.models import User
from eures_beta.users.test_accounts import (
    ACCOUNTS,
    PWA_ACCOUNTS,
    enabled,
    fictional_database,
    prepared_user,
)


class Command(BaseCommand):
    help = 'Add linked fictional local/preview journeys, preserving existing test data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minimal',
            action='store_true',
            help='Only the small foundational fixture used by focused automated tests.',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Read-only counts of every active model; do not seed.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not enabled() or not fictional_database():
            raise CommandError(
                'Test seeding requires an explicitly enabled local/preview database with only .invalid accounts.'
            )
        if options['report']:
            from eures_beta.users.preview_data.report import report

            report(self.stdout)
            return
        accounts = {**ACCOUNTS, **PWA_ACCOUNTS}
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
        from eures_beta.users.demo_employers import consolidate_employers

        consolidate_employers()
        call_command('sync_group_and_perms', stdout=self.stdout)
        call_command('seed_matching_trial', stdout=self.stdout)
        # Leave a separate, answered fixture ready for the invitation push trial.
        match = CandidateOfferMatch.objects.get(
            candidate__user=users['candidate-pwa-replay'], offer__source_kind='matching'
        )
        if (
            match.decision == 'pending'
            and not CandidateOfferReview.objects.filter(match=match).exists()
        ):
            from eures_beta.matching import services

            evaluation = match.evaluations.order_by('-pk').first()
            services.decide(
                match.pk,
                evaluation.pk,
                'retained',
                by_adviser=users['adviser'],
            )
            confirmation = CandidateOfferReview.objects.create(
                match=match, requested_by_adviser=users['adviser']
            )
            for row in offer_review_services.review_state(confirmation)['rows']:
                if row['askable']:
                    offer_review_services.answer(
                        match.candidate.user,
                        confirmation.pk,
                        row['key'],
                        row['fingerprint'],
                        'yes',
                    )
        if not options['minimal']:
            from eures_beta.users.preview_data.scenarios import seed_scenarios

            seed_scenarios(users)
        self.stdout.write(
            'Fictional test accounts and offers are ready; existing data preserved.'
        )
