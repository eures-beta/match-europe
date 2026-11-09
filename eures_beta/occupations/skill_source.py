"""Read pinned official exports locally; model output never defines a concept."""

import csv
import hashlib
import io
import json
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


def prepare_occupation_files(directory, skills, relations):
    """Build disposable small slices only after the pinned archives were verified."""
    destination = Path(directory) / ('prepared-' + VERSION)
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for uri, linked in relations.items():
        name = hashlib.sha256(uri.encode()).hexdigest() + '.json'
        raw = json.dumps(
            {
                'occupation': uri,
                'skills': {key: skills[key] for key in linked},
                'relations': linked,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
        temporary = destination / (name + '.tmp')
        temporary.write_bytes(raw)
        temporary.replace(destination / name)
        files[name] = hashlib.sha256(raw).hexdigest()
    temporary = destination / 'manifest.tmp'
    temporary.write_text(
        json.dumps({'version': VERSION, 'files': files}, sort_keys=True)
    )
    temporary.replace(destination / 'manifest.json')
    prepared_manifest.cache_clear()


@lru_cache(maxsize=1)
def prepared_manifest(directory):
    path = Path(directory) / ('prepared-' + VERSION) / 'manifest.json'
    if not path.exists():
        return None
    manifest = json.loads(path.read_text())
    if manifest['version'] != VERSION:
        raise ValueError('Prepared source version mismatch')
    return manifest['files']


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
    directory = str(settings.SKILLS_ALBERT_SOURCE_DIR)
    manifest = prepared_manifest(directory)
    if manifest is not None:
        name = hashlib.sha256(uri.encode()).hexdigest() + '.json'
        if name not in manifest:
            raise ValueError('No verified relations')
        raw = (Path(directory) / ('prepared-' + VERSION) / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest[name]:
            raise ValueError('Prepared source checksum mismatch')
        value = json.loads(raw)
        if value['occupation'] != uri or not value['relations']:
            raise ValueError('Prepared source occupation mismatch')
        return value['skills'], value['relations']
    skills, relations = load_source(directory)
    linked = relations.get(uri, {})
    if not linked:
        raise ValueError('No verified relations')
    return skills, linked
