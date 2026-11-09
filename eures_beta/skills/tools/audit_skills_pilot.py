"""Audit pilot JSON against the pinned ESCO CSV archives, without network or DB."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

LANGUAGES = ('fr', 'en', 'de')
PINNED = {
    'fr': '84fe49774fad90bdfd27d080440ffb1fdef1fbd62939f6436d2fc21f4d58d4e8',
    'en': 'f9761b0b52be1828b38a3e5e0ae59a93a7b0ce358bc800f52f57a8b002adeb3e',
    'de': 'a4d12661e9d4208e7e4583b6a2268d0a8c6d31618f7df2d46e90831d95e06d51',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_index(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), f'Duplicate {key}')
    return result


def audit(data_dir, esco_dir):
    pilot = json.loads((data_dir / 'occupation_skills.json').read_text())
    source = json.loads((data_dir / 'occupation_skills_sources.json').read_text())
    tables = {}
    for lang in LANGUAGES:
        archive = esco_dir / f'esco-1.2.1-{lang}.zip'
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        require(digest == PINNED[lang], f'Archive checksum mismatch: {lang}')
        for document in (pilot, source):
            require(
                document['metadata']['escoVersion'] == '1.2.1', 'Wrong ESCO version'
            )
            entry = next(
                row
                for row in document['metadata']['sources']
                if row['name'] == f'ESCO {lang}'
            )
            require(entry['sha256'] == digest, f'Metadata checksum mismatch: {lang}')
        with zipfile.ZipFile(archive) as bundle:
            tables[lang] = {}
            for kind in (
                'occupations',
                'skills',
                'occupationSkillRelations',
                'transversalSkillsCollection',
            ):
                with bundle.open(f'{kind}_{lang}.csv') as handle:
                    tables[lang][kind] = list(
                        csv.DictReader(io.TextIOWrapper(handle, encoding='utf-8-sig'))
                    )

    occupations = unique_index(source['occupations'], 'uri')
    skills = unique_index(source['skills'], 'uri')
    for lang in LANGUAGES:
        transversal = {
            row['conceptUri'] for row in tables[lang]['transversalSkillsCollection']
        }
        for kind, records in (('occupations', occupations), ('skills', skills)):
            official = {row['conceptUri']: row for row in tables[lang][kind]}
            for uri, record in records.items():
                require(uri in official, f'Unknown official {kind} URI: {uri}')
                row = official[uri]
                require(bool(record['labels'][lang]), f'Empty label: {uri} / {lang}')
                require(
                    record['labels'][lang] == row['preferredLabel'],
                    f'Label differs from ESCO: {uri} / {lang}',
                )
                require(
                    record['descriptions'][lang] == row['description'],
                    f'Description differs from ESCO: {uri} / {lang}',
                )
                if kind == 'skills':
                    require(
                        record['alternativeLabels'][lang]
                        == row['altLabels'].splitlines(),
                        f'Alternative labels differ: {uri} / {lang}',
                    )
                    for field in ('skillType', 'reuseLevel'):
                        require(record[field] == row[field], f'{field} differs: {uri}')
                    require(
                        record['inOfficialTransversalCollection']
                        == (uri in transversal),
                        f'Transversal membership differs: {uri} / {lang}',
                    )

    actual_relations = {
        (r['occupationUri'], r['skillUri'], r['relationType'], r['skillType'])
        for r in source['occupationSkillRelations']
    }
    require(
        len(actual_relations) == len(source['occupationSkillRelations']),
        'Duplicate source relation',
    )
    for lang in LANGUAGES:
        expected = {
            (r['occupationUri'], r['skillUri'], r['relationType'], r['skillType'])
            for r in tables[lang]['occupationSkillRelations']
            if r['occupationUri'] in occupations and r['skillUri'] in skills
        }
        require(actual_relations == expected, f'Official relations differ: {lang}')

    cards = list(pilot['cards'])
    alternative = pilot['cleaningAlternative']
    domestic = next(c for c in cards if c['id'] == 'nettoyage')
    cards.append({**domestic, **alternative, 'id': 'nettoyage-locaux'})
    unique_index(cards, 'id')
    require(len(cards) == 50, 'Expected 50 cards including cleaning alternative')
    require(
        len({card['occupation']['uri'] for card in cards}) == 50,
        'Expected 50 distinct occupation URIs',
    )
    require(
        {card['occupation']['uri'] for card in cards} == set(occupations),
        'Source occupations differ from cards',
    )
    require(
        pilot['selectionRules']['keySkillsMax'] == 5
        and pilot['selectionRules']['behavioursMax'] == 3
        and pilot['selectionRules']['preselected'] is False,
        'Selection rules differ from the existing pilot',
    )
    editorial = official_behaviours = 0
    for card in cards:
        uri = card['occupation']['uri']
        require(card['occupation'] == occupations[uri], f'Occupation differs: {uri}')
        used = set()
        for group, count in (('keySkills', 8), ('behaviours', 4)):
            require(len(card[group]) == count, f'Wrong {group} count: {uri}')
            for item in card[group]:
                skill = item['skillUri']
                require(skill in skills, f'Unknown skill: {skill}')
                require(skill not in used, f'Duplicate selection: {uri} / {skill}')
                used.add(skill)
                relation = item['occupationRelation']
                official = (
                    uri,
                    skill,
                    relation['type'],
                    skills[skill]['skillType'],
                ) in actual_relations
                if group == 'keySkills':
                    require(official, f'Unofficial key skill: {uri} / {skill}')
                    require(
                        relation['origin'] == 'ESCO 1.2.1 occupationSkillRelations',
                        f'Wrong key skill origin: {uri} / {skill}',
                    )
                else:
                    require(
                        item['inOfficialTransversalCollection']
                        == skills[skill]['inOfficialTransversalCollection'],
                        f'Behaviour membership differs: {uri} / {skill}',
                    )
                    if relation['type'] is None:
                        require(
                            relation['origin']
                            == 'editorial_suggestion_not_official_occupation_relation',
                            f'Missing editorial origin: {uri} / {skill}',
                        )
                        editorial += 1
                    else:
                        require(
                            official, f'Invented behaviour relation: {uri} / {skill}'
                        )
                        official_behaviours += 1
    return {
        'status': 'passed',
        'escoVersion': '1.2.1',
        'archiveSha256': PINNED,
        'occupationCount': len(cards),
        'distinctSkillCount': len(skills),
        'officialSourceRelationCount': len(actual_relations),
        'verifiedKeySkillSelections': len(cards) * 8,
        'behaviourSelections': len(cards) * 4,
        'behavioursWithOfficialOccupationRelation': official_behaviours,
        'behavioursMarkedEditorial': editorial,
        'languagesVerified': list(LANGUAGES),
        'method': 'Exact comparison with pinned official CSV archives; no network',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esco-dir', type=Path, required=True)
    parser.add_argument(
        '--data-dir', type=Path, default=Path(__file__).parents[1] / 'data'
    )
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit(args.data_dir, args.esco_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
