"""Fetch a PR description without shell redirection or stale success artifacts."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def fetch_description(number, root=ROOT):
    if not re.fullmatch(r'[1-9][0-9]*', number):
        raise ValueError(
            'Indiquer un numéro de PR positif : make pr-description PR=195'
        )
    directory = root / '.runtime'
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / f'pr-{number}-description.md'
    # A failed refresh must not leave an older description usable as fresh data.
    target.unlink(missing_ok=True)
    result = subprocess.run(
        [
            'gh',
            'pr',
            'view',
            number,
            '--repo',
            'eures-beta/match-europe',
            '--json',
            'body',
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    body = json.loads(result.stdout)['body']
    if not isinstance(body, str):
        raise ValueError('GitHub a renvoyé une description invalide')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=directory, delete=False
        ) as output:
            temporary = Path(output.name)
            output.write(body)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main():
    try:
        target = fetch_description(os.environ.get('MATCH_PR_NUMBER', ''))
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.strip() or 'Lecture GitHub échouée')
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f'Description non enregistrée : {error}')
    print(target)


if __name__ == '__main__':
    main()
