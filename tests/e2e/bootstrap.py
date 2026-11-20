"""Initialize a fresh fictional DB, then exec the real production web server."""

import os
import subprocess
from pathlib import Path


def main():
    for arguments in (('migrate', 'users', '0001_initial'), ('migrate',)):
        subprocess.run(['python', 'manage.py', *arguments, '--noinput'], check=True)
    if Path('eures_beta/skills/common_source.py').exists():
        # Run the real preview hook twice, in fresh processes, under the same
        # container memory limit. Keep demo/email flags scoped to this seed.
        seed_environment = {
            **os.environ,
            'DJANGO_ENVIRONMENT': 'preview',
            'DEMO_ACCOUNTS_ENABLED': '1',
            'EMAIL_DELIVERY_ENABLED': '0',
        }
        for _ in range(2):
            subprocess.run(
                ['python', 'manage.py', 'seed_test_accounts'],
                env=seed_environment,
                check=True,
            )
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    User = get_user_model()
    for role in ('adviser', 'employer'):
        User.objects.create_user(email=f'{role}@example.invalid', kind=role)
    call_command('sync_group_and_perms')
    os.execvp(
        'gunicorn',
        [
            'gunicorn',
            'config.wsgi:application',
            '--bind',
            '0.0.0.0:8443',
            '--workers',
            '1',
            '--worker-class',
            'gthread',
            '--threads',
            '8',
            '--timeout',
            '30',
            '--no-control-socket',
            '--certfile',
            '/artifacts/tls/cert.pem',
            '--keyfile',
            '/artifacts/tls/key.pem',
        ],
    )


if __name__ == '__main__':
    main()
