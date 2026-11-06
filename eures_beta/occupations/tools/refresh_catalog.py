"""Explicit operator imports; never used by application requests or startup."""

import copy
import csv
import hashlib
import io
import json
import re
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests

from eures_beta.occupations.catalog import DATA_DIR
from .build_catalog import LANGUAGES, MAPPING_URL, ROME_URL, read_csv, xlsx_rows

FILES = ('esco.json', 'rome.json', 'ogr.json', 'esco_rome.json')
HOSTS = {'ec.europa.eu', 'esco.ec.europa.eu', 'www.francetravail.org'}
LIMIT = 64 * 1024 * 1024


def download(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != 'https'
        or parsed.hostname not in HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError(
            'Only HTTPS downloads from official ESCO/France Travail hosts are allowed'
        )
    with requests.get(
        url, timeout=(10, 60), stream=True, allow_redirects=False
    ) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Expected HTTP 200; redirects are not followed')
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > LIMIT:
                raise ValueError('Source exceeds the 64 MiB download limit')
            chunks.append(chunk)
    return b''.join(chunks)


def archive(raw):
    result = zipfile.ZipFile(io.BytesIO(raw))
    if sum(info.file_size for info in result.infolist()) > 256 * 1024 * 1024:
        result.close()
        raise ValueError('Archive exceeds the 256 MiB expanded limit')
    return result


def parse_esco(raws):
    jobs = {}
    for language, raw in zip(LANGUAGES, raws, strict=True):
        with archive(raw) as source:
            rows = read_csv(source, f'occupations_{language}.csv')
            seen = {}
            for row in rows:
                if row['status'] != 'released':
                    raise ValueError('Non-released ESCO occupation')
                uri = row['conceptUri']
                if not re.fullmatch(
                    r'http://data.europa.eu/esco/occupation/[0-9a-f-]{36}', uri
                ):
                    raise ValueError('Invalid ESCO URI')
                normalized = {k: v for k, v in row.items() if k != 'modifiedDate'}
                if uri in seen and seen[uri] != normalized:
                    raise ValueError('Conflicting duplicate ESCO occupation')
                seen[uri] = normalized
                job = jobs.setdefault(
                    uri,
                    {
                        'uri': uri,
                        'code': row['code'],
                        'iscoGroup': row['iscoGroup'],
                        'labels': {},
                        'aliases': {},
                        'descriptions': {},
                        'broader': [],
                    },
                )
                if (job['code'], job['iscoGroup']) != (row['code'], row['iscoGroup']):
                    raise ValueError('ESCO identifiers differ between languages')
                for field, source_field in (
                    ('labels', 'preferredLabel'),
                    ('descriptions', 'description'),
                ):
                    value = row[source_field].strip()
                    if not value:
                        raise ValueError('Missing ESCO translation')
                    job[field][language] = value
                job['aliases'][language] = sorted(
                    set(
                        filter(
                            None,
                            (
                                row['altLabels'] + '\n' + row['hiddenLabels']
                            ).splitlines(),
                        )
                    )
                )
            if not seen or set(seen) != set(jobs):
                raise ValueError(
                    'ESCO languages must contain the same nonempty set of occupations'
                )
            if language == 'en':
                for row in read_csv(source, 'broaderRelationsOccPillar_en.csv'):
                    if row['conceptUri'] in jobs:
                        jobs[row['conceptUri']]['broader'].append(row['broaderUri'])
    if any(set(job['labels']) != set(LANGUAGES) for job in jobs.values()):
        raise ValueError('ESCO languages are incomplete')
    for job in jobs.values():
        job['broader'] = sorted(set(job['broader']))
    return sorted(jobs.values(), key=lambda row: row['uri'])


def parse_rome(raw):
    # Parse the official XLSX as XML, without executing macros or external links.
    with archive(raw):
        pass
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'rome.xlsx'
        source.write_bytes(raw)
        rows = list(xlsx_rows(source, expected_sheet=None))
    fiches, appellations = {}, {}
    for a, b, c, label, ogr in rows:
        if (
            not re.fullmatch(r'[A-Z]', a)
            or not re.fullmatch(r'\d{2}', b)
            or not re.fullmatch(r'\d{2}', c)
        ):
            continue
        if not label or not ogr.isdigit():
            raise ValueError('Invalid ROME label or OGR identifier')
        code = a + b + c
        if code not in fiches:
            fiches[code] = {'code': code, 'label': label, 'id': ogr}
        else:
            entry = appellations.setdefault(
                ogr, {'id': ogr, 'label': label, 'ficheCodes': []}
            )
            if entry['label'] != label:
                raise ValueError('Conflicting OGR labels')
            if code not in entry['ficheCodes']:
                entry['ficheCodes'].append(code)
    if not fiches or not appellations:
        raise ValueError('Empty ROME or OGR export')
    return fiches, appellations


def parse_mapping(raw):
    rows = list(csv.reader(io.StringIO(raw.decode('cp1252')), delimiter=';'))
    metadata = {row[0].strip(): row[1].strip() for row in rows[:14] if len(row) >= 2}
    versions = (
        metadata.get('Classification 1 Version'),
        metadata.get('Classification 2 Version'),
    )
    if not all(versions):
        raise ValueError('Missing ESCO/ROME mapping version metadata')
    mappings = []
    for row in rows:
        if len(row) < 9 or not row[0].startswith(
            'http://data.europa.eu/esco/occupation/'
        ):
            continue
        if not row[5].isdigit() or not row[6] or not row[8]:
            raise ValueError('Invalid mapping row')
        mappings.append(
            {'escoUri': row[0], 'id': row[5], 'label': row[6], 'relation': row[8]}
        )
    if not mappings:
        raise ValueError('Empty ESCO/ROME mapping')
    return mappings, versions


def encode(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    ).encode('utf-8')


def read_bundle(directory):
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    values = {}
    for name in FILES:
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest['artifacts'][name]['sha256']:
            raise ValueError(f'Checksum mismatch: {name}')
        values.update(json.loads(raw))
    return manifest, values


def refresh(
    kind, output, *, version=None, source_url=None, allow_removals=False, fetch=download
):
    output = Path(output)
    if output.is_symlink():
        raise ValueError('Output directory must not be a symlink')
    baseline = output if (output / 'manifest.json').exists() else DATA_DIR
    manifest, values = read_bundle(baseline)
    before = copy.deepcopy(values)
    sources = manifest['sources']
    if kind == 'esco':
        version = version or manifest['version']
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Expected an explicit ESCO semantic version')
        raws = []
        for lang in LANGUAGES:
            url = f'https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v{version}%20-%20classification%20-%20{lang}%20-%20csv.zip'
            raw = fetch(url)
            raws.append(raw)
            sources[LANGUAGES.index(lang)] = {
                'name': f'ESCO {lang}',
                'version': version,
                'url': url,
                'sha256': hashlib.sha256(raw).hexdigest(),
            }
        values['occupations'] = parse_esco(raws)
        for source in sources[:3]:
            source['occupationCount'] = len(values['occupations'])
        manifest['version'] = version
    elif kind == 'rome':
        url = source_url or sources[4]['url'] or ROME_URL
        if source_url and not version:
            raise ValueError('--source-version is required with a new ROME source URL')
        raw = fetch(url)
        values['fiches'], values['appellations'] = parse_rome(raw)
        previous_source = sources[4]
        sources[4] = {
            **(previous_source if url == previous_source['url'] else {}),
            'name': 'ROME hierarchy',
            'url': url,
            'version': version or sources[4]['version'],
            'sha256': hashlib.sha256(raw).hexdigest(),
        }
    elif kind == 'mapping':
        url = source_url or sources[3]['url'] or MAPPING_URL
        raw = fetch(url)
        values['mappings'], versions = parse_mapping(raw)
        previous_source = sources[3]
        sources[3] = {
            **(previous_source if url == previous_source['url'] else {}),
            'name': 'ESCO/ROME mapping',
            'url': url,
            'version': f'ESCO {versions[0]} / ROME {versions[1]}',
            'sha256': hashlib.sha256(raw).hexdigest(),
        }
    else:
        raise ValueError('Unknown source')
    # Recompute only derived relations, never infer an equivalence from labels.
    by_uri = {job['uri']: job for job in values['occupations']}
    for job in by_uri.values():
        job['rome'] = []
    for match in values['mappings']:
        match['ficheCodes'] = (
            values['appellations'].get(match['id'], {}).get('ficheCodes', [])
        )
        if match['escoUri'] in by_uri:
            by_uri[match['escoUri']]['rome'].append(
                {k: v for k, v in match.items() if k != 'escoUri'}
            )
    for job in by_uri.values():
        job['romeFiches'] = [
            values['fiches'][code]
            for code in sorted(
                {code for row in job['rome'] for code in row['ficheCodes']}
            )
        ]
        job['romeUnresolved'] = sorted(
            {row['id'] for row in job['rome'] if not row['ficheCodes']}
        )
    report = {}
    for key, identifier in (
        ('occupations', 'uri'),
        ('fiches', 'code'),
        ('appellations', 'id'),
    ):
        old = (
            {row[identifier]: row for row in before[key]}
            if isinstance(before[key], list)
            else before[key]
        )
        new = (
            {row[identifier]: row for row in values[key]}
            if isinstance(values[key], list)
            else values[key]
        )
        report[key] = {
            'added': sorted(new.keys() - old.keys()),
            'removed': sorted(old.keys() - new.keys()),
            'changed': sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
        }
        if report[key]['removed'] and not allow_removals:
            raise ValueError(
                f'{key}: removed identifiers; review source and rerun with --allow-removals'
            )
    counts = manifest['counts']
    counts.update(
        occupations=len(by_uri),
        romeFiches=len(values['fiches']),
        romeAppellations=len(values['appellations']),
        romeAppellationRows=sum(
            len(a['ficheCodes']) for a in values['appellations'].values()
        ),
        mappingRows=len(values['mappings']),
        occupationsWithRome=sum(bool(j['rome']) for j in by_uri.values()),
        occupationsWithFicheCodes=sum(bool(j['romeFiches']) for j in by_uri.values()),
        mappingUrisAbsentFromEsco=len(
            {m['escoUri'] for m in values['mappings']} - by_uri.keys()
        ),
        unresolvedRomeAppellationIds=sorted(
            {m['id'] for m in values['mappings'] if not m['ficheCodes']}
        ),
    )
    if kind == 'esco':
        for lang, raw in zip(LANGUAGES, raws, strict=True):
            with archive(raw) as source:
                row_count = len(read_csv(source, f'occupations_{lang}.csv'))
            counts[f'esco_{lang}_sourceRows'] = row_count
            counts[f'esco_{lang}_duplicateRows'] = row_count - len(by_uri)
            counts[f'esco_{lang}'] = len(by_uri)
    encoded = {
        name: encode({key: values[key]})
        for name, key in zip(
            FILES, ('occupations', 'fiches', 'appellations', 'mappings'), strict=True
        )
    }
    manifest['artifacts'] = {
        name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        for name, raw in encoded.items()
    }
    if any(values[key] != before[key] for key in before):
        manifest['retrieved'] = date.today().isoformat()
    report['mappingRows'] = {
        'before': len(before['mappings']),
        'after': len(values['mappings']),
    }
    # Finish all downloads, parsing and validation before touching the output.
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary)
        for name, raw in {
            **encoded,
            'manifest.json': encode(manifest),
            'update-report.json': encode(report),
        }.items():
            (stage / name).write_bytes(raw)
        read_bundle(stage)
        for name in (*FILES, 'manifest.json', 'update-report.json'):
            (stage / name).replace(output / name)
    return report
