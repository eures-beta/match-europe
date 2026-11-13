"""At most six real calls, fixed fictional inputs, no database or raw output."""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from eures_beta.matching import dialogue_albert as adapter

CASES = {
    'fr': (
        'Un samedi sur deux pourrait me convenir.',
        'Oui, cela concerne uniquement cette offre.',
    ),
    'en': (
        'Every other Saturday could work for me.',
        'Yes, this applies to this offer only.',
    ),
    'de': (
        'Jeden zweiten Samstag könnte ich arbeiten.',
        'Ja, das gilt nur für dieses Stellenangebot.',
    ),
}


class Command(BaseCommand):
    help = 'Evaluate the real Albert dialogue with six bounded fictional exchanges.'

    def add_arguments(self, parser):
        parser.add_argument('--live', action='store_true')

    def handle(self, *args, **options):
        if (
            not options['live']
            or not settings.ALBERT_API_KEY
            or settings.ALBERT_SIMULATED
        ):
            raise CommandError('Explicit live opt-in and configured access required.')
        row = {
            'kind': 'schedule',
            'presented': {
                'expected': {
                    'slots': ['saturday:morning'],
                    'mandatory': True,
                    'text': '',
                },
                'declared': {'schedule_saturday': ['morning'], 'schedule_strict': True},
            },
        }
        for language, (first, second) in CASES.items():
            try:
                initial = adapter.ask(
                    row, first, '', language, [{'role': 'candidate', 'text': first}]
                )
                if initial['outcome'] != 'clarify':
                    raise adapter.Unavailable
                history = [
                    {'role': 'candidate', 'text': first},
                    {'role': 'assistant', 'text': initial['reply']},
                    {'role': 'candidate', 'text': second},
                ]
                result = adapter.ask(
                    row, first + '\n' + second, 'offer', language, history
                )
                if (
                    result['outcome'] != 'conditional'
                    or result['scope'] != 'offer'
                    or result['changes']
                ):
                    raise adapter.Unavailable
            except adapter.Unavailable:
                raise CommandError(
                    'Albert dialogue evaluation failed; no raw response is logged.'
                ) from None
            self.stdout.write(
                language + ': clarification and offer-specific reservation validated'
            )
