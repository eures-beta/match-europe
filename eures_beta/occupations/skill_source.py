"""Read pinned official exports locally; model output never defines a concept."""

import csv
import hashlib
import io
from functools import lru_cache
from pathlib import Path
import zipfile

from django.conf import settings
from .catalog import occupation_index
from .tools.audit_skills_pilot import PINNED

VERSION = (
    'esco-1.2.1-'
    + hashlib.sha256(str(sorted(PINNED.items())).encode()).hexdigest()[:16]
)


@lru_cache(maxsize=1)
def load_source(directory):
    skills = {}
    relations = {}
    for language, expected in PINNED.items():
        path = Path(directory) / f'esco-1.2.1-{language}.zip'
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Official archive checksum mismatch')
        with zipfile.ZipFile(path) as bundle:
            with bundle.open(f'skills_{language}.csv') as handle:
                for row in csv.DictReader(
                    io.TextIOWrapper(handle, encoding='utf-8-sig')
                ):
                    skills.setdefault(row['conceptUri'], {'labels': {}})['labels'][
                        language
                    ] = row['preferredLabel']
            if language == 'fr':
                with bundle.open('occupationSkillRelations_fr.csv') as handle:
                    for row in csv.DictReader(
                        io.TextIOWrapper(handle, encoding='utf-8-sig')
                    ):
                        if row['relationType'] in ('essential', 'optional'):
                            relations.setdefault(row['occupationUri'], {})[
                                row['skillUri']
                            ] = row['relationType']
    if any(
        not all(item['labels'].get(lang) for lang in PINNED) for item in skills.values()
    ):
        raise ValueError('Incomplete official translations')
    if any(uri not in skills for rows in relations.values() for uri in rows):
        raise ValueError('Unknown official skill')
    return skills, relations


def source_for(uri):
    if uri not in occupation_index():
        raise ValueError('Unknown occupation')
    skills, relations = load_source(str(settings.SKILLS_ALBERT_SOURCE_DIR))
    linked = relations.get(uri, {})
    if not linked:
        raise ValueError('No verified relations')
    return skills, linked
