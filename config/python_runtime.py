"""Check official CPython tags and lock the corresponding Docker image.

No third-party packages, Git mutations, credentials or application services.
The scheduled workflow publishes the two resulting files atomically in a PR.
"""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STABLE_TAG = re.compile(r'refs/tags/v(3\.\d+\.\d+)')
CLEVER_PYTHON_URL = (
    'https://www.clever.cloud/developers/doc/deploy/applications/python/'
)


class RuntimeTables(HTMLParser):
    """Read table cells, ignoring examples and unrelated prose on the page."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.table is not None:
                raise ValueError('Unexpected nested runtime table')
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def clever_python_versions(document):
    parser = RuntimeTables()
    parser.feed(document)
    tables = [
        table for table in parser.tables if table and 'Accepted Versions' in table[0]
    ]
    if len(tables) != 1 or parser.table is not None:
        raise ValueError('Cannot identify the official Clever Python version table')
    table = tables[0]
    column = table[0].index('Accepted Versions')
    versions = set()
    for row in table[1:]:
        if len(row) != len(table[0]):
            raise ValueError('Invalid Clever Python version table row')
        value = row[column]
        if value in ('', '2', '3'):
            continue
        match = re.fullmatch(r'(3\.\d+)( \(EOL\))?', value)
        if not match:
            raise ValueError('Unrecognized Clever Python version entry')
        if not match[2]:
            versions.add(match[1])
    if not versions:
        raise ValueError('No maintained Clever Python branch found')
    return versions


def latest_version(refs, current, supported=None):
    versions = [match[1] for ref in refs if (match := STABLE_TAG.fullmatch(ref['ref']))]
    if not versions:
        raise ValueError('No stable CPython tag found; refusing an empty update')
    if supported is not None:
        versions = [v for v in versions if '.'.join(v.split('.')[:2]) in supported]
        if not versions:
            return None
    latest = max(versions, key=lambda value: tuple(map(int, value.split('.'))))
    current_tuple = tuple(map(int, current.split('.')))
    latest_tuple = tuple(map(int, latest.split('.')))
    if latest_tuple <= current_tuple:
        return None
    return latest


def read_https(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        # All URLs are fixed trusted service endpoints, never user input.
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS required')
        data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError('Registry response too large')
        return data


def image_digest(version):
    if not re.fullmatch(r'3\.\d+\.\d+', version):
        raise ValueError('Expected a stable Python version')
    token = json.loads(
        read_https(
            'https://auth.docker.io/token?service=registry.docker.io'
            '&scope=repository:library/python:pull'
        )
    )['token']
    manifest = read_https(
        f'https://registry-1.docker.io/v2/library/python/manifests/{version}-slim',
        {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.oci.image.index.v1+json, '
            'application/vnd.docker.distribution.manifest.list.v2+json',
        },
    )
    document = json.loads(manifest)
    platforms = {
        (item['platform'].get('os'), item['platform'].get('architecture'))
        for item in document.get('manifests', [])
    }
    if not {('linux', 'amd64'), ('linux', 'arm64')} <= platforms:
        raise ValueError('Python image not available for both Linux architectures')
    return 'sha256:' + hashlib.sha256(manifest).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    current = (ROOT / '.python-version').read_text().strip()
    if args.verify:
        expected = tuple(map(int, current.split('.')))
        if sys.version_info[: len(expected)] != expected:
            raise SystemExit(f'Expected Python {current}; recreate the environment')
        return
    result = subprocess.run(
        ['gh', 'api', 'repos/python/cpython/git/matching-refs/tags/v3.'],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    supported = clever_python_versions(read_https(CLEVER_PYTHON_URL).decode('utf-8'))
    refs = json.loads(result.stdout)
    newest = latest_version(refs, current)
    if newest and '.'.join(newest.split('.')[:2]) not in supported:
        print(f'Skipping Python {newest}: branch absent from {CLEVER_PYTHON_URL}')
    latest = latest_version(refs, current, supported)
    target = latest or current
    if '.'.join(target.split('.')[:2]) not in supported:
        print(f'Python {current}: branch not supported by Clever; no proposal')
        return
    if not latest and not re.fullmatch(r'3\.\d+\.\d+', current):
        print(f'Python {current}: no newer stable release supported by Clever')
        return
    if not re.fullmatch(r'3\.\d+\.\d+', target):
        raise ValueError('Cannot resolve an exact stable runtime')
    digest = image_digest(target)  # Resolve before writing either file.
    old_digest = (ROOT / '.python-image-digest').read_text().strip()
    if latest or digest != old_digest:
        if args.update:
            (ROOT / '.python-version').write_text(target + '\n')
            (ROOT / '.python-image-digest').write_text(digest + '\n')
        print(f'Python {current} -> {target}; Docker {digest}; Clever branch supported')
    else:
        print(f'Python {current}: no newer stable release')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.strip() or 'Official CPython lookup failed')
