"""Validate a staged catalog offline, with varied multilingual search checks."""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from eures_beta.occupations import catalog as service

QUERIES = {
    'fr': [
        'soudeur',
        'comptable',
        'infirmier',
        'architecte',
        'bibliothécaire',
        'psychologue',
        'boulanger',
        'pharmacien',
        'électricien',
        'développeur',
        'orthophoniste',
        'menuisier',
    ],
    'en': [
        'welder',
        'accountant',
        'nurse',
        'architect',
        'librarian',
        'psychologist',
        'baker',
        'pharmacist',
        'electrician',
        'software developer',
    ],
    'de': [
        'Schweißer',
        'Buchhalter',
        'Krankenpfleger',
        'Architekt',
        'Bibliothekar',
        'Psychologe',
        'Bäcker',
        'Apotheker',
        'Elektriker',
    ],
}


def validate(directory, previous=None):
    service.DATA_DIR = directory
    manifest = service.catalog()['manifest']
    jobs = service.catalog()['occupations']
    rome = service.rome_catalog()
    for name, info in manifest['artifacts'].items():
        if (
            hashlib.sha256((directory / name).read_bytes()).hexdigest()
            != info['sha256']
        ):
            raise ValueError('Checksum mismatch')
    assert len(jobs) == len({job['uri'] for job in jobs}) == 3039
    assert len(rome['fiches']) == 1923
    assert len(rome['appellations']) == 14330
    assert len(rome['mappings']) == manifest['counts']['mappingRows']
    for job in jobs:
        assert re.fullmatch(
            r'http://data.europa.eu/esco/occupation/[0-9a-f-]{36}', job['uri']
        )
        for lang in service.LANGUAGES:
            assert job['labels'][lang].strip() and job['descriptions'][lang].strip()
            assert isinstance(job['aliases'][lang], list)
        for fiche in job['romeFiches']:
            assert fiche == rome['fiches'][fiche['code']]
            assert re.fullmatch(r'[A-Z][0-9]{4}', fiche['code'])
        for match in job['rome']:
            assert match['ficheCodes'] == rome['appellations'].get(match['id'], {}).get(
                'ficheCodes', []
            )
    report = {'counts': manifest['counts'], 'searchChecks': [], 'delta': None}
    for lang, queries in QUERIES.items():
        for query in queries:
            started = time.perf_counter()
            results = service.suggestions(query, lang)
            assert results, f'No results: {lang} {query}'
            report['searchChecks'].append(
                {
                    'language': lang,
                    'query': query,
                    'labels': [row['label'] for row in results],
                    'milliseconds': round((time.perf_counter() - started) * 1000, 2),
                }
            )
    assert not service.suggestions('xyzqzzzz métier introuvable', 'fr')
    assert not service.suggestions('', 'fr')
    if previous:
        old = {
            job['uri']: job for job in json.loads(previous.read_text())['occupations']
        }
        new = service.occupation_index()
        report['delta'] = {
            'previousSample': len(old),
            'added': len(set(new) - set(old)),
            'removed': sorted(set(old) - set(new)),
            'changedLabels': [
                uri
                for uri in set(old) & set(new)
                if old[uri]['labels'] != new[uri]['labels']
            ],
        }
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.directory, args.previous)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(
        json.dumps(
            {
                'counts': report['counts'],
                'searchChecks': len(report['searchChecks']),
                'maxMilliseconds': max(
                    row['milliseconds'] for row in report['searchChecks']
                ),
                'delta': report['delta'],
            },
            ensure_ascii=False,
        )
    )
