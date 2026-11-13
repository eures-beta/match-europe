"""Disposable Docker isolation; all PR code runs without host or service secrets."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
LEGACY = '464b68f0707d2d238dbf92450f1c062f3f4a2093'
MEMORY = 256 * 1024 * 1024


def command(*args, check=True, timeout=300):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        # Commands contain only generated local test credentials. Never inherit
        # the host environment into a container via an unrestricted --env flag.
        raise RuntimeError(f'{args[0]} {args[1]} failed: {result.stderr[-1500:]}')
    return result


def snapshot(destination, legacy):
    if legacy:
        archive = destination.parent / 'legacy.tar'
        with archive.open('wb') as output:
            subprocess.run(
                ['git', 'archive', LEGACY], cwd=ROOT, stdout=output, check=True
            )
        with tarfile.open(archive) as source:
            source.extractall(destination, filter='data')
        shutil.copytree(
            ROOT / 'eures_beta/e2e',
            destination / 'eures_beta/e2e',
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('__pycache__'),
        )
    else:
        files = command(
            'git',
            '-C',
            str(ROOT),
            'ls-files',
            '--cached',
            '--others',
            '--exclude-standard',
            '-z',
        ).stdout
        for name in files.split('\0'):
            if not name:
                continue
            source = ROOT / name
            if not source.is_file():
                continue
            if source.is_symlink():
                raise ValueError('Symlink in test build context requires review')
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def wait_for(predicate, label, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(1)
    raise TimeoutError(label)


def inspect(container):
    return json.loads(command('docker', 'inspect', container).stdout)[0]


def memory(container):
    result = command(
        'docker',
        'exec',
        container,
        'cat',
        '/sys/fs/cgroup/memory.peak',
        '/sys/fs/cgroup/memory.events',
        '/sys/fs/cgroup/memory.max',
        check=False,
    )
    if result.returncode:
        return {'container_oom_killed': inspect(container)['State']['OOMKilled']}
    lines = result.stdout.splitlines()
    return {
        'peak_bytes': int(lines[0]),
        'limit_bytes': int(lines[-1]),
        **{key: int(value) for key, value in (line.split() for line in lines[1:-1])},
    }


def run(legacy=False):
    identifier = 'me-e2e-' + uuid.uuid4().hex[:12]
    image, network = identifier + '-image', identifier + '-net'
    app, fixture, database = (
        identifier + suffix for suffix in ('-web', '-fixtures', '-db')
    )
    probe_name = identifier + '-probe'
    containers = [probe_name, app, fixture, database]
    # Bind-mounted artifacts must remain removable by the host on Linux too.
    owner = f'{os.getuid()}:{os.getgid()}'
    report = {'legacy_control': legacy, 'source': LEGACY if legacy else 'working-tree'}
    phase = 'build'
    with tempfile.TemporaryDirectory(prefix='match-europe-e2e-') as temp:
        directory = Path(temp)
        artifacts = directory / 'artifacts'
        artifacts.mkdir(mode=0o700)
        context = directory / 'source'
        context.mkdir()
        try:
            snapshot(context, legacy)
            print(
                f'Building isolated {"legacy" if legacy else "current"} test image',
                flush=True,
            )
            command(
                'docker',
                'build',
                '--tag',
                image,
                '--file',
                str(context / 'eures_beta/e2e/Dockerfile'),
                str(context),
                timeout=600,
            )
            image_info = json.loads(
                command('docker', 'image', 'inspect', image).stdout
            )[0]
            report['architecture'] = image_info['Architecture']
            command('docker', 'network', 'create', '--internal', network)
            phase = 'fixtures'
            command(
                'docker',
                'run',
                '--detach',
                '--name',
                fixture,
                '--user',
                owner,
                '--sysctl',
                'net.ipv4.ip_unprivileged_port_start=0',
                '--network',
                network,
                '--network-alias',
                'albert.api.etalab.gouv.fr',
                '--memory',
                '128m',
                '--volume',
                f'{artifacts}:/artifacts',
                image,
                'python',
                '-m',
                'eures_beta.e2e.fixtures',
            )
            wait_for(
                lambda: (artifacts / 'fixture-ready').exists(), 'TLS fixture startup'
            )
            command(
                'docker',
                'run',
                '--detach',
                '--name',
                database,
                '--network',
                network,
                '--network-alias',
                'database',
                '--memory',
                '512m',
                '--env',
                'POSTGRES_USER=e2e',
                '--env',
                'POSTGRES_PASSWORD=fictional-database-password',
                '--env',
                'POSTGRES_DB=e2e',
                'postgres:17-bookworm',
            )
            wait_for(
                lambda: command(
                    'docker', 'exec', database, 'pg_isready', '-U', 'e2e', check=False
                ).returncode
                == 0,
                'PostgreSQL startup',
            )
            environment = {
                'DJANGO_SETTINGS_MODULE': 'eures_beta.e2e.settings',
                'DJANGO_SECRET_KEY': 'isolated-fictional-system-tests-only',
                'DJANGO_ENVIRONMENT': 'production',
                'DJANGO_DEBUG': '0',
                'DJANGO_ALLOWED_HOSTS': 'web',
                'DJANGO_HTTPS': '1',
                'PGHOST': 'database',
                'PGDATABASE': 'e2e',
                'PGUSER': 'e2e',
                'PGPASSWORD': 'fictional-database-password',
                'PGPORT': '5432',
                'EMAIL_DELIVERY_ENABLED': '1',
                'LOGIN_EMAIL_ENABLED': '1',
                'EMAIL_HOST': 'captured.invalid',
                'DEFAULT_FROM_EMAIL': 'sender@example.invalid',
                'LOGIN_EMAIL_ORIGIN': 'https://web:8443',
                'TEST_ACCOUNTS_ENABLED': '0',
                'ALBERT_IMPORT_ENABLED': '1',
                'ALBERT_IMPORT_SIMULATED': '0',
                'ALBERT_API_KEY': 'fictional-e2e-key',
                'SSL_CERT_FILE': '/artifacts/tls/cert.pem',
                'HOME': '/tmp',
            }
            env_file = directory / 'environment'
            env_file.write_text(
                ''.join(f'{key}={value}\n' for key, value in environment.items())
            )
            phase = 'startup'
            command(
                'docker',
                'run',
                '--detach',
                '--name',
                app,
                '--user',
                owner,
                '--network',
                network,
                '--network-alias',
                'web',
                '--memory',
                '256m',
                '--memory-swap',
                '256m',
                '--cpus',
                '1',
                '--pids-limit',
                '128',
                '--env-file',
                str(env_file),
                '--volume',
                f'{artifacts}:/artifacts',
                image,
            )
            configuration = inspect(app)['HostConfig']
            assert configuration['Memory'] == MEMORY
            assert configuration['MemorySwap'] == MEMORY
            probe = [
                'docker',
                'run',
                '--rm',
                '--name',
                probe_name,
                '--user',
                owner,
                '--network',
                network,
                '--memory',
                '128m',
                '--volume',
                f'{artifacts}:/artifacts',
                image,
                'python',
                '-m',
                'eures_beta.e2e.journeys',
            ]
            wait_for(
                lambda: command(
                    *probe, '--health-only', check=False, timeout=15
                ).returncode
                == 0,
                'Gunicorn startup',
            )
            phase = 'journeys'
            print(
                'Running real HTTPS journeys against one 256 MiB worker container',
                flush=True,
            )
            result = command(
                *probe, *(['--search-only'] if legacy else []), check=False, timeout=180
            )
            summary = artifacts / 'journeys.json'
            report['journeys'] = (
                json.loads(summary.read_text())
                if summary.exists()
                else {'success': False, 'phase': 'runner'}
            )
            log_result = command('docker', 'logs', app, check=False)
            logs = log_result.stdout + log_result.stderr
            report['memory'] = memory(app)
            report['worker_starts'] = logs.count('Booting worker with pid:')
            report['sigkill'] = 'was sent SIGKILL' in logs
            report['occupation_request_started'] = '"route":"occupation_search"' in logs
            report['albert_calls'] = json.loads(
                (artifacts / 'albert-calls.json').read_text()
            )['calls']
            if legacy:
                report['success'] = bool(
                    result.returncode != 0
                    and report['journeys'].get('phase') == 'occupation-cold'
                    and report['occupation_request_started']
                    and (
                        report['memory'].get('oom_kill', 0) > 0
                        or report['memory'].get('container_oom_killed')
                    )
                )
            else:
                report['success'] = bool(
                    result.returncode == 0
                    and report['journeys'].get('success')
                    and report['memory'].get('limit_bytes') == MEMORY
                    and report['memory'].get('oom_kill', 1) == 0
                    and report['worker_starts'] == 1
                    and not report['sigkill']
                    and report['albert_calls'] >= 1
                )
        except Exception as error:
            report.update(success=False, phase=phase, error=type(error).__name__)
            # Diagnostic logs remain in memory and are never uploaded with mail/TLS keys.
            print(
                f'Isolated test failed during {phase}: {type(error).__name__}',
                flush=True,
            )
        finally:
            for container in containers:
                command(
                    'docker',
                    'rm',
                    '--force',
                    '--volumes',
                    container,
                    check=False,
                    timeout=30,
                )
            command('docker', 'network', 'rm', network, check=False, timeout=30)
            command('docker', 'image', 'rm', image, check=False, timeout=30)
    output = ROOT / '.runtime'
    output.mkdir(exist_ok=True)
    path = output / ('e2e-legacy-report.json' if legacy else 'e2e-report.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report.get('success') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-control', action='store_true')
    raise SystemExit(run(parser.parse_args().legacy_control))
