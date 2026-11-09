"""Rebuild the small pilot source catalogue from pinned official CSV archives."""

import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from django.core.management.base import BaseCommand, CommandError

from eures_beta.occupations.skills_pilot import DATA


class Command(BaseCommand):
    help = 'Reconstruire les données du pilote depuis les exports ESCO 1.2.1 locaux, en staging uniquement.'

    def add_arguments(self, parser):
        parser.add_argument('--esco-dir', required=True)
        parser.add_argument('--output', default='.runtime/skills-pilot-staging')

    def handle(self, *args, **options):
        source = json.loads((DATA / 'occupation_skills_sources.json').read_text())
        pilot = json.loads((DATA / 'occupation_skills.json').read_text())
        output = Path(options['output'])
        if output.resolve() == DATA.resolve():
            raise CommandError(
                'La reconstruction doit rester en staging ; revoir le diff avant promotion manuelle.'
            )
        occupations = {item['uri'] for item in source['occupations']}
        skill_uris = {item['uri'] for item in source['skills']}
        tables = {}
        try:
            for lang in ('fr', 'en', 'de'):
                archive = Path(options['esco_dir']) / f'esco-1.2.1-{lang}.zip'
                expected = next(
                    s['sha256']
                    for s in source['metadata']['sources']
                    if s['name'] == f'ESCO {lang}'
                )
                if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
                    raise CommandError(
                        f'Archive {lang} différente de la version ESCO épinglée : revue explicite requise.'
                    )
                with zipfile.ZipFile(archive) as bundle:
                    tables[lang] = {}
                    for table in (
                        'occupations',
                        'skills',
                        'occupationSkillRelations',
                        'transversalSkillsCollection',
                    ):
                        with bundle.open(f'{table}_{lang}.csv') as handle:
                            rows = list(
                                csv.DictReader(
                                    io.TextIOWrapper(handle, encoding='utf-8-sig')
                                )
                            )
                        tables[lang][table] = rows
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            raise CommandError(
                'Archives officielles complètes FR/EN/DE requises.'
            ) from exc
        for lang, data in tables.items():
            occ_index = {row['conceptUri']: row for row in data['occupations']}
            skill_index = {row['conceptUri']: row for row in data['skills']}
            for item in source['occupations']:
                row = occ_index[item['uri']]
                item['labels'][lang] = row['preferredLabel']
                item['descriptions'][lang] = row['description']
            for item in source['skills']:
                row = skill_index[item['uri']]
                item['labels'][lang] = row['preferredLabel']
                item['descriptions'][lang] = row['description']
                item['alternativeLabels'][lang] = row['altLabels'].splitlines()
                item['skillType'] = row['skillType']
                item['reuseLevel'] = row['reuseLevel']
                item['inOfficialTransversalCollection'] = any(
                    r['conceptUri'] == item['uri']
                    for r in data['transversalSkillsCollection']
                )
        relations = [
            {
                'occupationUri': r['occupationUri'],
                'skillUri': r['skillUri'],
                'relationType': r['relationType'],
                'skillType': r['skillType'],
            }
            for r in tables['fr']['occupationSkillRelations']
            if r['occupationUri'] in occupations and r['skillUri'] in skill_uris
        ]
        relations.sort(key=lambda row: (row['occupationUri'], row['skillUri']))
        source['occupationSkillRelations'] = relations
        for card in pilot['cards'] + [pilot['cleaningAlternative']]:
            uri = card['occupation']['uri']
            record = next(item for item in source['occupations'] if item['uri'] == uri)
            card['occupation'] = record
        # Stable metadata identifies the fixed source edition; no invented latest/version discovery.
        output.mkdir(parents=True, exist_ok=True)
        for name, value in [
            ('occupation_skills_sources.json', source),
            ('occupation_skills.json', pilot),
        ]:
            (output / name).write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + '\n'
            )
        self.stdout.write(
            self.style.SUCCESS(
                'Deux fichiers reconstruits en staging, sans changement des données versionnées.'
            )
        )
