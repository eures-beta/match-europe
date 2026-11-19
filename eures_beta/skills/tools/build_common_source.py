"""Build portable, individually verified official ESCO and ROME occupation slices."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from .audit_skills_pilot import PINNED
from eures_beta.occupations.tools.build_descriptions import EXPECTED_ARCHIVE, SOURCE


def build(esco_dir, rome_archive, output):
    skills = {}
    relations = {}
    for language, expected in PINNED.items():
        path = esco_dir / ('esco-1.2.1-' + language + '.zip')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Unexpected ESCO archive')
        with ZipFile(path) as bundle:
            for row in csv.DictReader(
                io.StringIO(
                    bundle.read('skills_' + language + '.csv').decode('utf-8-sig')
                )
            ):
                item = skills.setdefault(
                    row['conceptUri'],
                    {
                        'labels': {},
                        'kind': 'skill',
                        'scheme': 'ESCO',
                        'skillType': row['skillType'],
                    },
                )
                item['labels'][language] = row['preferredLabel']
            if language == 'fr':
                for row in csv.DictReader(
                    io.StringIO(
                        bundle.read('occupationSkillRelations_fr.csv').decode(
                            'utf-8-sig'
                        )
                    )
                ):
                    if row['relationType'] in ('essential', 'optional'):
                        relations.setdefault(row['occupationUri'], {})[
                            row['skillUri']
                        ] = row['relationType']
    if any(
        not all(item['labels'].get(lang) for lang in PINNED) for item in skills.values()
    ):
        raise ValueError('Incomplete ESCO translations')
    if hashlib.sha256(rome_archive.read_bytes()).hexdigest() != EXPECTED_ARCHIVE:
        raise ValueError('Unexpected ROME archive')
    with ZipFile(rome_archive) as source:
        rome = json.loads(
            source.read('unix_fiche_emploi_metier_v462.json').decode('cp1252')
        )
    # Explicit, reviewed reading aids from the initial trial; other ROME labels stay French.
    baker = json.loads(
        (Path(__file__).parents[1] / 'data' / 'baker_mixed.json').read_text()
    )
    translated = {
        row['sources'][0]['id']: row['labels']
        for group in ('skills', 'behaviours')
        for row in baker[group]
        if len(row['sources']) == 1 and row['sources'][0]['scheme'] == 'ROME'
    }
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'common_skill_source.zip'
    files = {}
    label_index = {key: row['labels'] for key, row in skills.items()}

    def write(bundle, name, value):
        raw = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(',', ':')
        ).encode()
        info = ZipInfo(name, date_time=(2026, 10, 19, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        bundle.writestr(info, raw)
        files[name] = hashlib.sha256(raw).hexdigest()

    with ZipFile(destination, 'w', compression=ZIP_DEFLATED, compresslevel=9) as bundle:
        for uri, linked in sorted(relations.items()):
            write(
                bundle,
                'esco/' + uri.rsplit('/', 1)[1] + '.json',
                {
                    'reference': uri,
                    'skills': {key: skills[key] for key in linked},
                    'relations': linked,
                },
            )
        for fiche in sorted(rome, key=lambda row: row['rome']['code_rome']):
            code = fiche['rome']['code_rome']
            rows = {}
            linked = {}
            for source_kind, kind in [
                ('savoir_faire', 'skill'),
                ('savoir_etre_professionnel', 'behaviour'),
            ]:
                for group in (
                    fiche['competences'].get(source_kind, {}).get('enjeux', [])
                ):
                    for item in group['items']:
                        key = 'rome:competence:' + str(item['code_ogr'])
                        rows[key] = {
                            'labels': translated.get(
                                str(item['code_ogr']), {'fr': item['libelle']}
                            ),
                            'originalLabel': item['libelle'],
                            'kind': kind,
                            'scheme': 'ROME',
                        }
                        linked[key] = (
                            'essential'
                            if item.get('coeur_metier') == 'Principale'
                            else 'optional'
                        )
                        label_index[key] = rows[key]['labels']
            write(
                bundle,
                'rome/' + code + '.json',
                {'reference': 'rome:' + code, 'skills': rows, 'relations': linked},
            )
        write(bundle, 'labels.json', label_index)
    version = (
        'common-esco121-rome26m10-'
        + hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    )
    manifest = {
        'version': version,
        'sources': {
            'esco': PINNED,
            'rome': {'url': SOURCE, 'sha256': EXPECTED_ARCHIVE},
        },
        'files': files,
        'archiveSha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    }
    (output / 'common_skill_source_manifest.json').write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + '\n'
    )
    print('official_slices', len(files), 'archive_bytes', destination.stat().st_size)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esco-dir', type=Path, required=True)
    parser.add_argument('--rome-archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.esco_dir, args.rome_archive, args.output)
