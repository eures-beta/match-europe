"""Check official CPython tags and lock the corresponding Docker image.

No third-party packages, Git mutations, credentials or application services.
The scheduled workflow publishes the two resulting files atomically in a PR.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STABLE_TAG = re.compile(r'refs/tags/v(3\.\d+\.\d+)')


def latest_version(refs, current):
    versions = [match[1] for ref in refs if (match := STABLE_TAG.fullmatch(ref['ref']))]
    if not versions:
        raise ValueError('No stable CPython tag found; refusing an empty update')
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
    latest = latest_version(json.loads(result.stdout), current)
    target = latest or current
    if not re.fullmatch(r'3\.\d+\.\d+', target):
        raise ValueError('Cannot resolve an exact stable runtime')
    digest = image_digest(target)  # Resolve before writing either file.
    old_digest = (ROOT / '.python-image-digest').read_text().strip()
    if latest or digest != old_digest:
        if args.update:
            (ROOT / '.python-version').write_text(target + '\n')
            (ROOT / '.python-image-digest').write_text(digest + '\n')
        print(f'Python {current} -> {target}; Docker {digest}')
    else:
        print(f'Python {current}: no newer stable release')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.strip() or 'Official CPython lookup failed')
