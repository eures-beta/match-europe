"""Apply the new user schema before resolving switched historical dependencies."""

import sys
from django.core.management.commands.migrate import Command as DjangoMigrate
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder
from django.test.utils import override_settings


def clear_migration_modules():
    # Historical swappable dependencies are evaluated when modules are imported.
    for name in list(sys.modules):
        if '.migrations.' in name and not name.startswith('django.db.'):
            sys.modules.pop(name, None)


class Command(DjangoMigrate):
    def handle(self, *args, **options):
        connection = connections[options['database']]
        applied = MigrationRecorder(connection).applied_migrations()
        if (
            ('users', '0001_initial') not in applied
            and not options.get('plan')
            and not options.get('check_unapplied')
        ):
            if (
                ('employers', '0001_autonomous_schema') not in applied
                and 'journeys_employerimport' in connection.introspection.table_names()
            ):
                raise RuntimeError(
                    'Apply the autonomous migration transition before switching users.'
                )
            clear_migration_modules()
            try:
                with override_settings(AUTH_USER_MODEL='auth.User'):
                    bootstrap = dict(
                        options,
                        app_label='users',
                        migration_name='0001_initial',
                        interactive=False,
                        fake=False,
                        fake_initial=False,
                        plan=False,
                        check_unapplied=False,
                        run_syncdb=False,
                    )
                    super().handle(*args, **bootstrap)
            finally:
                clear_migration_modules()
        return super().handle(*args, **options)
