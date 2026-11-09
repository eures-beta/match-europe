from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from eures_beta.skills.skill_source import load_source, VERSION


class Command(BaseCommand):
    help = 'Vérifier les archives ESCO épinglées FR/EN/DE, sans réseau.'

    def handle(self, *args, **options):
        try:
            skills, relations = load_source(str(settings.SKILLS_ALBERT_SOURCE_DIR))
        except Exception as exc:
            raise CommandError('Archives ESCO absentes ou non conformes.') from exc
        self.stdout.write(
            f'{VERSION}: {len(skills)} concepts, {len(relations)} métiers avec relations officielles.'
        )
