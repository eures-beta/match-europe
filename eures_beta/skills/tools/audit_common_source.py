"""Check every portable slice without a network request or a database mutation."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def audit(directory):
    manifest = json.loads((directory / 'common_skill_source_manifest.json').read_text())
    counts = {'occupations': 0, 'relations': 0, 'skills': set(), 'emptyTechnical': []}
    with (directory / 'common_skill_source.zip').open('rb') as handle:
        if (
            hashlib.file_digest(handle, 'sha256').hexdigest()
            != manifest['archiveSha256']
        ):
            raise ValueError('Archive checksum mismatch')
    with ZipFile(directory / 'common_skill_source.zip') as bundle:
        if set(bundle.namelist()) != set(manifest['files']):
            raise ValueError('Unindexed source entries')
        for name, expected in manifest['files'].items():
            raw = bundle.read(name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Slice checksum mismatch: ' + name)
            value = json.loads(raw)
            if name == 'labels.json':
                continue
            if set(value['skills']) != set(value['relations']):
                raise ValueError('Unlinked skill')
            for key, item in value['skills'].items():
                if not item['labels'].get('fr') or item['kind'] not in (
                    'skill',
                    'behaviour',
                ):
                    raise ValueError('Invalid skill')
                if item['scheme'] == 'ESCO' and not all(
                    item['labels'].get(lang) for lang in ('fr', 'en', 'de')
                ):
                    raise ValueError('Missing ESCO translation')
                if item['scheme'] == 'ROME' and not key.startswith('rome:competence:'):
                    raise ValueError('Invalid ROME reference')
            counts['occupations'] += 1
            counts['relations'] += len(value['relations'])
            counts['skills'].update(value['skills'])
            if not any(
                item['kind'] == 'skill' and item.get('skillType') != 'knowledge'
                for item in value['skills'].values()
            ):
                counts['emptyTechnical'].append(value['reference'])
    counts['skills'] = len(counts['skills'])
    return counts


if __name__ == '__main__':
    print(json.dumps(audit(Path(__file__).parents[1] / 'data'), sort_keys=True))
