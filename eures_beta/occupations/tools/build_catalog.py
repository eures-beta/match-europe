"""Build complete, deterministic offline occupations catalogs from official sources.

No network, database or application dependency. Raw sources stay outside Git.
"""

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

LANGUAGES = ('fr', 'en', 'de')
ESCO_VERSION = '1.2.1'
MAPPING_URL = 'https://esco.ec.europa.eu/system/files/2025-12/EURESmapping_occs_FR.csv'
ROME_URL = 'https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/ROME/261014-rome_arboprincipale-octobre-2026.xlsx'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(archive, name):
    with archive.open(name) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig')))


def xlsx_rows(path):
    with zipfile.ZipFile(path) as archive:
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            strings = [''.join(node.itertext()) for node in root.findall('m:si', NS)]
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.find('m:sheets', NS)
        if sheets[1].attrib['name'] != 'Arbo Principale 19-10-2026':
            raise ValueError('ROME worksheet/version changed; review importer')
        root = ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
        for row in root.findall('.//m:row', NS):
            values = [''] * 5
            for cell in row.findall('m:c', NS):
                col = re.sub(r'[0-9]', '', cell.attrib['r'])
                if col not in 'ABCDE' or len(col) != 1:
                    continue
                value = cell.find('m:v', NS)
                text = value.text if value is not None else ''
                if cell.attrib.get('t') == 's':
                    text = strings[int(text)]
                elif cell.attrib.get('t') == 'inlineStr':
                    text = ''.join(cell.find('m:is', NS).itertext())
                values[ord(col) - ord('A')] = (text or '').strip()
            yield values


def build(esco_dir, mapping_path, rome_path, output):
    jobs, sources, stats = {}, [], {}
    for lang in LANGUAGES:
        path = esco_dir / f'esco-{ESCO_VERSION}-{lang}.zip'
        with zipfile.ZipFile(path) as archive:
            if archive.testzip():
                raise ValueError('Corrupt ESCO archive')
            rows = read_csv(archive, f'occupations_{lang}.csv')
            ids = [row['conceptUri'] for row in rows]
            if any(row['status'] != 'released' for row in rows):
                raise ValueError('Non-released occupation')
            unique = {}
            for row in rows:
                value = {key: val for key, val in row.items() if key != 'modifiedDate'}
                if row['conceptUri'] in unique and unique[row['conceptUri']] != value:
                    raise ValueError('Conflicting duplicate occupation')
                unique[row['conceptUri']] = value
            stats[f'esco_{lang}_sourceRows'] = len(rows)
            stats[f'esco_{lang}_duplicateRows'] = len(rows) - len(unique)
            rows = list(unique.values())
            if jobs and set(ids) != set(jobs):
                raise ValueError('Languages do not contain the same occupations')
            for row in rows:
                if not row['preferredLabel'].strip() or not row['description'].strip():
                    raise ValueError('Missing label or description')
                job = jobs.setdefault(
                    row['conceptUri'],
                    {
                        'uri': row['conceptUri'],
                        'code': row['code'],
                        'iscoGroup': row['iscoGroup'],
                        'labels': {},
                        'aliases': {},
                        'descriptions': {},
                        'broader': [],
                        'rome': [],
                    },
                )
                if job['code'] != row['code'] or job['iscoGroup'] != row['iscoGroup']:
                    raise ValueError('Language-specific identifier mismatch')
                job['labels'][lang] = row['preferredLabel'].strip()
                job['aliases'][lang] = sorted(
                    set(
                        filter(
                            None,
                            (
                                row['altLabels'] + '\n' + row['hiddenLabels']
                            ).splitlines(),
                        )
                    )
                )
                job['descriptions'][lang] = row['description'].strip()
            if lang == 'en':
                relations = read_csv(archive, f'broaderRelationsOccPillar_{lang}.csv')
                for row in relations:
                    if row['conceptUri'] in jobs:
                        jobs[row['conceptUri']]['broader'].append(row['broaderUri'])
        sources.append(
            {
                'name': f'ESCO {lang}',
                'version': ESCO_VERSION,
                'url': f'https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v{ESCO_VERSION}%20-%20classification%20-%20{lang}%20-%20csv.zip',
                'sha256': digest(path),
                'occupationCount': len(rows),
            }
        )
        stats[f'esco_{lang}'] = len(rows)
    if len(jobs) < 3000:
        raise ValueError('Expected complete catalog, not a sample')

    fiches, appellations = {}, {}
    appellation_rows = 0
    for a, b, c, label, ogr in xlsx_rows(rome_path):
        if (
            not re.fullmatch(r'[A-Z]', a)
            or not re.fullmatch(r'\d{2}', b)
            or not re.fullmatch(r'\d{2}', c)
        ):
            continue
        code = a + b + c
        if not ogr.isdigit() or not label:
            raise ValueError('Missing ROME heading or appellation')
        if code not in fiches:
            fiches[code] = {'code': code, 'label': label, 'id': ogr}
        else:
            appellation_rows += 1
            entry = appellations.setdefault(
                ogr, {'id': ogr, 'label': label, 'ficheCodes': []}
            )
            if entry['label'] != label:
                raise ValueError('Ambiguous ROME appellation label')
            if code not in entry['ficheCodes']:
                entry['ficheCodes'].append(code)
    if len(fiches) != 1923 or appellation_rows != 14330:
        raise ValueError(
            f'ROME completeness changed: {len(fiches)} fiches / {appellation_rows} appellations; review source version'
        )

    all_mapping = list(
        csv.reader(
            io.StringIO(mapping_path.read_bytes().decode('cp1252')), delimiter=';'
        )
    )
    metadata = {row[0].strip(): row[1].strip() for row in all_mapping[:14]}
    if (
        metadata.get('Classification 1 Version') != '1.0.9'
        or metadata.get('Classification 2 Version') != '25M06'
    ):
        raise ValueError('ESCO/ROME mapping version changed')
    mappings = []
    for row in all_mapping:
        if len(row) < 9 or not row[0].startswith(
            'http://data.europa.eu/esco/occupation/'
        ):
            continue
        match = {
            'escoUri': row[0],
            'id': row[5],
            'label': row[6],
            'relation': row[8],
            'ficheCodes': appellations.get(row[5], {}).get('ficheCodes', []),
        }
        mappings.append(match)
        if row[0] in jobs:
            jobs[row[0]]['rome'].append(
                {k: v for k, v in match.items() if k != 'escoUri'}
            )
    missing_ids = sorted({row['id'] for row in mappings if not row['ficheCodes']})
    for job in jobs.values():
        codes = {code for row in job['rome'] for code in row['ficheCodes']}
        job['romeFiches'] = [fiches[code] for code in sorted(codes)]
        job['romeUnresolved'] = sorted(
            {row['id'] for row in job['rome'] if not row['ficheCodes']}
        )
        job['broader'] = sorted(set(job['broader']))
    stats.update(
        {
            'occupations': len(jobs),
            'romeFiches': len(fiches),
            'romeAppellations': len(appellations),
            'romeAppellationRows': appellation_rows,
            'mappingRows': len(mappings),
            'occupationsWithRome': sum(bool(job['rome']) for job in jobs.values()),
            'occupationsWithFicheCodes': sum(
                bool(job['romeFiches']) for job in jobs.values()
            ),
            'mappingUrisAbsentFromEsco': len(
                {row['escoUri'] for row in mappings} - set(jobs)
            ),
            'unresolvedRomeAppellationIds': missing_ids,
        }
    )
    sources.extend(
        [
            {
                'name': 'ESCO/ROME mapping',
                'url': MAPPING_URL,
                'version': 'V1.1; ESCO 1.0.9 / ROME 25M06',
                'date': '2025-11-19',
                'sha256': digest(mapping_path),
            },
            {
                'name': 'ROME hierarchy',
                'url': ROME_URL,
                'version': '26M10',
                'date': '2026-10-19',
                'sha256': digest(rome_path),
            },
        ]
    )
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name, value in [
        (
            'occupations.json.gz',
            {'occupations': sorted(jobs.values(), key=lambda row: row['uri'])},
        ),
        (
            'rome.json.gz',
            {'fiches': fiches, 'appellations': appellations, 'mappings': mappings},
        ),
    ]:
        encoded = json.dumps(
            value, ensure_ascii=False, separators=(',', ':'), sort_keys=True
        ).encode()
        path = output / name
        path.write_bytes(gzip.compress(encoded, mtime=0))
        artifacts[name] = {
            'sha256': digest(path),
            'bytes': path.stat().st_size,
            'uncompressedBytes': len(encoded),
        }
    manifest = {
        'schemaVersion': 1,
        'version': ESCO_VERSION,
        'languages': list(LANGUAGES),
        'scope': 'complete occupations pillar FR/EN/DE; complete ROME hierarchy and official France mapping',
        'retrieved': '2026-10-29',
        'sources': sources,
        'counts': stats,
        'artifacts': artifacts,
        'attribution': {
            'esco': 'European Union / European Commission, ESCO 1.2.1; CSV extracts merged without changing definitions',
            'rome': 'France Travail, ROME 26M10; official ESCO crosswalk 25M06; normalized and joined by OGR ID',
        },
    }
    (output / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    )
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esco-dir', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--rome', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.esco_dir, args.mapping, args.rome, args.output)
    print(json.dumps(manifest['counts'], ensure_ascii=False, indent=2))
