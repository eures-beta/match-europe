"""Explicit build-time retrieval of the pinned public ESCO exports, no AI API."""

import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from eures_beta.occupations.skill_source import load_source, prepare_occupation_files
from eures_beta.occupations.skills_pilot import DATA
from eures_beta.occupations.tools.audit_skills_pilot import PINNED


class Command(BaseCommand):
    help = 'Préparer les archives officielles épinglées ; téléchargement uniquement avec --download.'

    def add_arguments(self, parser):
        parser.add_argument('--download', action='store_true')

    def handle(self, *args, **options):
        directory = Path(settings.SKILLS_ALBERT_SOURCE_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        sources = json.loads((DATA / 'occupation_skills_sources.json').read_text())[
            'metadata'
        ]['sources']
        for language, digest in PINNED.items():
            path = directory / f'esco-1.2.1-{language}.zip'
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise CommandError(
                        'Archive existante non conforme ; revue requise.'
                    )
                continue
            if not options['download']:
                raise CommandError(
                    'Archives absentes. Utiliser --download pour les exports publics épinglés.'
                )
            url = next(
                source['url']
                for source in sources
                if source['name'] == f'ESCO {language}'
            )
            if not url.startswith('https://ec.europa.eu/esco/download/'):
                raise CommandError('Origine officielle invalide.')
            temporary = None
            try:
                total = 0
                checksum = hashlib.sha256()
                with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
                    temporary = Path(output.name)
                    with urlopen(url, timeout=45) as response:
                        while chunk := response.read(1024 * 1024):
                            total += len(chunk)
                            if total > 32 * 1024 * 1024:
                                raise ValueError('Archive too large')
                            checksum.update(chunk)
                            output.write(chunk)
                if checksum.hexdigest() != digest:
                    raise ValueError('Checksum mismatch')
                temporary.replace(path)
            except (OSError, ValueError):
                raise CommandError(
                    'Téléchargement ou empreinte ESCO non conforme.'
                ) from None
            finally:
                if temporary and temporary.exists():
                    temporary.unlink()
        load_source.cache_clear()
        skills, relations = load_source(str(directory))
        prepare_occupation_files(directory, skills, relations)
        self.stdout.write(
            f'Archives ESCO vérifiées : {len(skills)} concepts et {len(relations)} métiers.'
        )
