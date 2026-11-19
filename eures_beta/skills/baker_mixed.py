"""Bounded candidate trial; overlaps are editorial, never official equivalences."""

from functools import lru_cache
import json
from pathlib import Path

URI = 'http://data.europa.eu/esco/occupation/1aadb308-432a-4d01-b54b-b4f7f76dd419'
ROME = 'rome:D1102'


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(
        Path(__file__).with_name('data').joinpath('baker_mixed.json').read_text()
    )


def official_mapping():
    # The crosswalk identifies an appellation, joined to the current fiche by OGR.
    # broadMatch/closeMatch must never authorise this combined occupation card.
    from eures_beta.occupations.catalog import rome_catalog

    return next(
        (
            row
            for row in rome_catalog()['mappings']
            if row['escoUri'] == URI
            and row['id'] == '11573'
            and row['relation'] == 'skos:exactMatch'
            and 'D1102' in row['ficheCodes']
        ),
        None,
    )


def canonical(reference):
    return (
        URI
        if official_mapping() and reference in (ROME, 'esco:' + URI, URI)
        else reference
    )


def card(reference):
    if not official_mapping() or canonical(reference) != URI:
        return None
    data = catalogue()
    return {
        'occupation': data['occupation'],
        'keySkills': [{'skillUri': x['id']} for x in data['skills']],
        'behaviours': [{'skillUri': x['id']} for x in data['behaviours']],
        '_skills': {
            x['id']: x for group in ('skills', 'behaviours') for x in data[group]
        },
        'mixed': True,
    }


def metadata(selection):
    data = catalogue()
    rows = {x['id']: x for group in ('skills', 'behaviours') for x in data[group]}
    keys = selection['skills'] + selection['behaviours']
    return {
        'version': data['version'],
        'mappingStatus': data['metadata']['mappingStatus'],
        'occupationReferences': ['esco:' + URI, ROME],
        'occupationMapping': official_mapping(),
        'sources': {key: rows[key]['sources'] for key in keys},
    }
