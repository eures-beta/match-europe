"""Extract original French definitions from a pinned, official ROME ZIP."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

SOURCE = 'https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/json'
EXPECTED_ARCHIVE = 'eaf2923df8b51b6d7819f21e5eedd2c8e1689ccb42d6f356770169bb3178432f'


def build(archive, output):
    raw = archive.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_ARCHIVE:
        raise ValueError(
            'Unexpected ROME archive: review the source version before updating'
        )
    with ZipFile(archive) as source:
        rows = json.loads(
            source.read('unix_fiche_emploi_metier_v462.json').decode('cp1252')
        )
    definitions = {row['rome']['code_rome']: row['definition'].strip() for row in rows}
    if len(definitions) != 1923 or not all(definitions.values()):
        raise ValueError('Incomplete ROME descriptions')
    output.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            {'definitions': definitions}, ensure_ascii=False, sort_keys=True, indent=2
        )
        + '\n'
    ).encode()
    filename = 'rome_definitions.json'
    (output / filename).write_bytes(payload)
    manifest = {
        'version': '26M10',
        'publication': '2026-10-19',
        'language': 'fr',
        'source': SOURCE,
        'sourceSha256': digest,
        'count': len(definitions),
        'artifacts': {filename: {'sha256': hashlib.sha256(payload).hexdigest()}},
    }
    (output / 'rome_definitions_sources.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.archive, args.output)
