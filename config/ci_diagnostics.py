"""Read-only GitHub Actions diagnostics; no Django or application credentials."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DEFAULT_PATTERN = (
    r'FAIL(?:ED)?\b|ERROR\b|AssertionError|Traceback|Killed|Segmentation|'
    r'SIG\w+|out of memory|oom_kill|exit(?:ed)?(?: with)? (?:code|status)|'
    r'Process completed|make(?:\[\d+\])?: \*\*\*|cancel|terminat'
)
# Remove OSC hyperlinks/titles, CSI colours/cursor controls and remaining controls.
ESCAPES = re.compile(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]')
CONTROLS = re.compile(r'[^\S\n\t ]|[\x00-\x08\x0b-\x1f\x7f-\x9f]')
CACHE_ROOT = Path('.runtime/ci-logs')
MAX_LOG_BYTES = 32 * 1024 * 1024


class DiagnosticError(Exception):
    pass


def clean(text):
    return CONTROLS.sub('', ESCAPES.sub('', text.replace('\r\n', '\n')))


def gh(*args):
    try:
        result = subprocess.run(
            ['gh', *args], capture_output=True, timeout=90, check=False
        )
    except FileNotFoundError as exc:
        raise DiagnosticError(
            'Installer GitHub CLI (gh), puis utiliser gh auth login.'
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DiagnosticError(
            'GitHub ne répond pas après 90 s ; réessayer explicitement.'
        ) from exc
    if result.returncode:
        # Do not echo raw CLI errors, which may contain credentials or server content.
        raise DiagnosticError(
            f'Lecture GitHub impossible (gh, code {result.returncode}). '
            'Vérifier réseau, gh auth status, droits et disponibilité des logs ; '
            'aucun résultat vide ne vaut diagnostic.'
        )
    return result.stdout


def positive(value):
    if not re.fullmatch(r'[1-9][0-9]*', str(value)):
        raise argparse.ArgumentTypeError('Un identifiant entier positif est requis.')
    return int(value)


def repository(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise argparse.ArgumentTypeError('REPO doit être owner/repository, sans URL.')
    if any(part in {'.', '..'} for part in value.split('/')):
        raise argparse.ArgumentTypeError('REPO invalide.')
    return value


def load_run(repo, run_id):
    try:
        run = json.loads(
            gh(
                'run',
                'view',
                str(run_id),
                '--repo',
                repo,
                '--json',
                'databaseId,attempt,status,conclusion,headSha,url,jobs',
            )
        )
        if int(run['databaseId']) != run_id:
            raise ValueError('Unexpected run')
        run['attempt'] = positive(run['attempt'])
        for job in run['jobs']:
            job['databaseId'] = positive(job['databaseId'])
        return run
    except (ValueError, KeyError, TypeError, argparse.ArgumentTypeError) as exc:
        raise DiagnosticError(
            'Réponse GitHub invalide ; aucun diagnostic produit.'
        ) from exc


def job_log(repo, run, job, refresh=False, root=None):
    root = CACHE_ROOT if root is None else root
    directory = root / repo / str(run['databaseId']) / str(run['attempt'])
    path = directory / f"{job['databaseId']}.log"
    completed = job['status'] == 'completed'
    if completed and path.is_file() and not refresh:
        return path.read_text(encoding='utf-8'), 'cache local'
    raw = gh(
        'api',
        '--method',
        'GET',
        f"repos/{repo}/actions/jobs/{job['databaseId']}/logs",
        '--allow-escape-sequences',
    )
    if not raw.strip():
        raise DiagnosticError(
            'Logs vides ou pas encore disponibles ; réessayer plus tard.'
        )
    if len(raw) > MAX_LOG_BYTES:
        raise DiagnosticError(
            'Logs supérieurs à 32 Mio ; consulter le job dans GitHub.'
        )
    log = clean(raw.decode('utf-8', errors='replace'))
    # Running jobs can grow: never freeze an incomplete log in the cache.
    if completed:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        for parent in (
            root,
            root / repo.split('/')[0],
            root / repo,
            directory.parent,
            directory,
        ):
            parent.chmod(0o700)
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=directory, delete=False
        ) as stream:
            temp = Path(stream.name)
            try:
                stream.write(log)
                stream.close()
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
    return log, 'GitHub'


def excerpt(log, pattern, context, limit):
    lines = clean(log).splitlines()
    indices = set()
    for index, line in enumerate(lines):
        if pattern.search(line):
            indices.update(
                range(max(0, index - context), min(len(lines), index + context + 1))
            )
    selected = sorted(indices)
    previous = -2
    for index in selected[-limit:]:
        if index > previous + 1:
            print('…')
        print(f'{index + 1}: {lines[index][:2000]}')
        previous = index
    if len(selected) > limit:
        print(
            f'Extrait limité aux {limit} dernières lignes correspondantes ; '
            'préciser PATTERN ou augmenter LINES.'
        )
    if not selected:
        print(
            'Aucune ligne correspondante. Cela ne prouve pas la réussite du job ; '
            'essayer PATTERN=. ou consulter son URL.'
        )


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('action', choices=('status', 'errors'))
    result.add_argument(
        '--run', type=positive, default=os.environ.get('CI_RUN') or None
    )
    result.add_argument(
        '--repo',
        type=repository,
        default=os.environ.get('CI_REPO') or 'eures-beta/match-europe',
    )
    result.add_argument(
        '--job', type=positive, default=os.environ.get('CI_JOB') or None
    )
    result.add_argument(
        '--pattern', default=os.environ.get('CI_PATTERN') or DEFAULT_PATTERN
    )
    result.add_argument(
        '--context', type=int, default=os.environ.get('CI_CONTEXT') or 3
    )
    result.add_argument('--lines', type=int, default=os.environ.get('CI_LINES') or 200)
    result.add_argument(
        '--refresh', action='store_true', default=os.environ.get('CI_REFRESH') == '1'
    )
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if not args.run:
        argument_parser.error('RUN est requis (identifiant numérique GitHub Actions).')
    if not 0 <= args.context <= 20 or not 1 <= args.lines <= 2000:
        argument_parser.error('CONTEXT doit être entre 0 et 20, LINES entre 1 et 2000.')
    try:
        pattern = re.compile(args.pattern, re.IGNORECASE)
    except re.error:
        argument_parser.error('PATTERN doit être une expression régulière valide.')
    try:
        run = load_run(args.repo, args.run)
        print(
            clean(
                f"Run {args.run}, tentative {run['attempt']} : {run['status']} / {run['conclusion'] or 'en attente'}"
            )
        )
        print(clean(f"Commit {run['headSha']} — {run['url']}"))
        jobs = run['jobs']
        if args.job:
            jobs = [job for job in jobs if job['databaseId'] == args.job]
            if not jobs:
                raise DiagnosticError(
                    'JOB ne fait pas partie de cette tentative du run.'
                )
        for job in jobs:
            print(
                clean(
                    f"Job {job['databaseId']} : {job['name']} — {job['status']} / {job['conclusion'] or 'en attente'}"
                )
            )
            print(clean(job['url']))
        if args.action == 'status':
            return 0
        if not args.job:
            jobs = [
                job
                for job in jobs
                if job['conclusion'] not in ('success', 'skipped', None, '')
            ]
        if not jobs:
            print(
                'Aucun job en échec/annulé terminé ; utiliser JOB pour un job précis.'
            )
        for job in jobs:
            log, source = job_log(args.repo, run, job, args.refresh)
            print(f"\nJob {job['databaseId']} — logs : {source}")
            excerpt(log, pattern, args.context, args.lines)
        return 0
    except (DiagnosticError, OSError) as exc:
        print(f'Diagnostic indisponible : {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
