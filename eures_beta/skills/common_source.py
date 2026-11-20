"""Portable official skill union; no cross-reference skill equivalence is inferred."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile
import ijson
from eures_beta.occupations import unified
from eures_beta.occupations.catalog import catalog, normalize
from .skills_pilot import catalogue as pilot_catalogue

DATA = Path(__file__).with_name('data')
# The pinned FR label says mixing, but the official EN label/description say kneading.
# This reading aid changes no identity or occupation relation.
READING_AIDS = {
    'http://data.europa.eu/esco/skill/d87653a0-87b0-4c03-a44a-bf0a217431a2': {
        'fr': 'pétrir des denrées alimentaires'
    }
}


@lru_cache(maxsize=1)
def manifest():
    data = json.loads((DATA / 'common_skill_source_manifest.json').read_text())
    with (DATA / 'common_skill_source.zip').open('rb') as handle:
        if hashlib.file_digest(handle, 'sha256').hexdigest() != data['archiveSha256']:
            raise ValueError('Common source archive checksum mismatch')
    return data


def version():
    return (
        manifest()['version']
        + '-'
        + catalog()['manifest']['sources'][3]['sha256'][:8]
        + '-reading1'
    )


@lru_cache(maxsize=64)
def source_slice(reference):
    if reference.startswith('rome:'):
        name = 'rome/' + reference[5:] + '.json'
    else:
        name = 'esco/' + reference.rsplit('/', 1)[-1] + '.json'
    expected = manifest()['files'].get(name)
    if expected is None:
        raise ValueError('No official skill source')
    with ZipFile(DATA / 'common_skill_source.zip') as archive:
        raw = archive.read(name)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Common source slice checksum mismatch')
    result = json.loads(raw)
    if result['reference'] != reference:
        raise ValueError('Common source occupation mismatch')
    return result


def source_for(reference):
    key = unified.canonical(reference)
    refs = unified.occupation_references(key)
    skills = {}
    relations = {}
    for ref in refs:
        original = ref[5:] if ref.startswith('esco:') else ref
        source = source_slice(original)
        for skill, record in source['skills'].items():
            relation = source['relations'][skill]
            skills.setdefault(skill, {**record, 'sources': []})['sources'].append(
                {
                    'scheme': record['scheme'],
                    'id': skill,
                    'version': '1.2.1' if record['scheme'] == 'ESCO' else '26M10',
                    'relationship': 'official_occupation_skill',
                    'occupation': original,
                    'relation': relation,
                }
            )
            relations[skill] = relation
    # Preserve existing explicit editorial behaviour suggestions and legacy selections.
    cards, known = pilot_catalogue()
    card = next(
        (card for card in cards.values() if card['occupation']['uri'] == key), None
    )
    if card:
        for row in card['behaviours']:
            skill = row['skillUri']
            if skill in skills:
                skills[skill]['kind'] = 'behaviour'
            if skill not in skills:
                skills[skill] = {
                    'labels': known[skill]['labels'],
                    'kind': 'behaviour',
                    'scheme': 'ESCO',
                    'sources': [
                        {
                            'scheme': 'ESCO',
                            'id': skill,
                            'version': '1.2.1',
                            'relationship': 'editorial_behaviour_suggestion',
                        }
                    ],
                }
                relations[skill] = 'editorial'
    # For occupations without ROME behaviours, offer the existing transversal reading aids.
    if not any(row['kind'] == 'behaviour' for row in skills.values()):
        for skill, record in known.items():
            if any(
                item['skillUri'] == skill
                for card in cards.values()
                for item in card['behaviours']
            ):
                skills.setdefault(
                    skill,
                    {
                        'labels': record['labels'],
                        'kind': 'behaviour',
                        'scheme': 'ESCO',
                        'sources': [
                            {
                                'scheme': 'ESCO',
                                'id': skill,
                                'version': '1.2.1',
                                'relationship': 'editorial_transversal_suggestion',
                            }
                        ],
                    },
                )
                relations.setdefault(skill, 'editorial')
    for skill, aids in READING_AIDS.items():
        if skill in skills:
            skills[skill]['originalLabels'] = skills[skill]['labels']
            skills[skill]['labels'] = {**skills[skill]['labels'], **aids}
    from . import baker_mixed

    if key == baker_mixed.URI and baker_mixed.official_mapping():
        reviewed = baker_mixed.catalogue()
        for group in ('skills', 'behaviours'):
            for row in reviewed[group]:
                if row['id'] in skills:
                    skills[row['id']]['labels'] = row['labels']
    return {
        'key': key,
        'occupation': unified.resolve_reference(key, 'fr'),
        'references': refs,
        'skills': skills,
        'relations': relations,
        'version': version(),
    }


def ordered(source, kind):
    return sorted(
        (
            key
            for key, row in source['skills'].items()
            if row['kind'] == kind
            and (kind != 'skill' or row.get('skillType') != 'knowledge')
        ),
        key=lambda key: (
            source['relations'][key] != 'essential',
            normalize(source['skills'][key]['labels']['fr']),
            key,
        ),
    )


def balanced(source, maximum=12):
    # Keep a union of identifiers; duplicate wording is only skipped in the shortlist,
    # never converted into an equivalence or used to match historical declarations.
    result = []
    seen = set()
    ordered_keys = ordered(source, 'skill')
    queues = [
        [key for key in ordered_keys if source['skills'][key]['scheme'] == scheme]
        for scheme in ('ESCO', 'ROME')
    ]
    while any(queues) and len(result) < maximum:
        for queue in queues:
            if not queue:
                continue
            key = queue.pop(0)
            label = normalize(source['skills'][key]['labels']['fr'])
            if label not in seen:
                result.append(key)
                seen.add(label)
            if len(result) >= maximum:
                break
    return result


def metadata(source, selection):
    return {
        'version': source['version'],
        'occupationReferences': source['references'],
        'occupationMappings': [
            row
            for ref in source['references']
            if ref.startswith('rome:')
            for row in unified.pairs().get(ref[5:], {}).get('mappings', [])
        ],
        'mappingStatus': 'no_automatic_skill_equivalence',
        'sources': {
            key: source['skills'][key]['sources']
            for key in selection['skills'] + selection['behaviours']
        },
    }


@lru_cache(maxsize=512)
def skill_labels(key):
    """Retain only requested labels, after checking the whole source member."""
    with ZipFile(DATA / 'common_skill_source.zip') as archive:
        with archive.open('labels.json') as source:
            if (
                hashlib.file_digest(source, 'sha256').hexdigest()
                != manifest()['files']['labels.json']
            ):
                raise ValueError('Common label index checksum mismatch')
            source.seek(0)
            for reference, labels in ijson.kvitems(source, ''):
                if reference == key:
                    return labels
    return {}


def skill_label(key, language):
    labels = {**skill_labels(key), **READING_AIDS.get(key, {})}
    return labels.get(language, labels.get('fr', ''))
