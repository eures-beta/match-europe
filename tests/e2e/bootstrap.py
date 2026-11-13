"""Initialize a fresh fictional DB, then exec the real production web server."""

import os
import subprocess


def main():
    for arguments in (('migrate', 'users', '0001_initial'), ('migrate',)):
        subprocess.run(['python', 'manage.py', *arguments, '--noinput'], check=True)
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
