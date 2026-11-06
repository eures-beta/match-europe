"""Exercise the real legacy-to-users transition in a disposable local database."""

import copy
import os
import uuid

import django
import psycopg
from psycopg import sql


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.recorder import MigrationRecorder
    from django.test.utils import override_settings
    from django.utils import timezone
    from eures_beta.users.management.commands.migrate import clear_migration_modules

    config = copy.deepcopy(settings.DATABASES['default'])
    if config['HOST'] not in ('/tmp', '127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('This check accepts local PostgreSQL only.')
    name = 'users_upgrade_' + uuid.uuid4().hex
    parameters = dict(
        host=config['HOST'],
        port=config['PORT'],
        user=config['USER'],
        password=config['PASSWORD'],
        dbname='postgres',
        autocommit=True,
    )
    with psycopg.connect(**parameters) as maintenance:
        maintenance.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        config['NAME'] = name
        connections.databases['user_upgrade'] = config
        database = connections['user_upgrade']
        try:
            clear_migration_modules()
            with override_settings(AUTH_USER_MODEL='auth.User'):
                executor = MigrationExecutor(database)
                targets = [
                    node
                    for node in executor.loader.graph.leaf_nodes()
                    # Business apps added later can depend on the custom User.
                    # The legacy fixture must contain only the historical auth
                    # schema and the pre-transition employer schema.
                    if node[0] in ('auth', 'contenttypes', 'sessions', 'admin')
                ]
                targets.append(('employers', '0001_autonomous_schema'))
                executor.migrate(targets)
                state = executor.loader.project_state(targets).apps
                person = (
                    state.get_model('employers', 'EmployerIdentity')
                    .objects.using('user_upgrade')
                    .create(email='Contact@example.invalid')
                )
                company = (
                    state.get_model('employers', 'EmployerCompany')
                    .objects.using('user_upgrade')
                    .create(name='Fictional company')
                )
                state.get_model('employers', 'EmployerMembership').objects.using(
                    'user_upgrade'
                ).create(person_id=person.pk, company_id=company.pk)
                offer = (
                    state.get_model('employers', 'EmployerImport')
                    .objects.using('user_upgrade')
                    .create(
                        created_by_id=person.pk,
                        company_id=company.pk,
                        email=person.email,
                        source_kind='manual',
                        session_key='',
                        preparation_agreed_at=timezone.now(),
                        data={'description': 'Preserved fictional offer'},
                    )
                )
                operation = (
                    state.get_model('employers', 'EmployerSearchOperation')
                    .objects.using('user_upgrade')
                    .create(
                        offer_id=offer.pk,
                        requested_by_id=person.pk,
                        revision=1,
                        state='started',
                        scenario='fictional',
                    )
                )
                state.get_model('employers', 'EmployerSearchEvent').objects.using(
                    'user_upgrade'
                ).create(operation_id=operation.pk, actor_id=person.pk, state='started')
            clear_migration_modules()
            recorder = MigrationRecorder(database)
            recorder.record_unapplied('employers', '0001_autonomous_schema')
            try:
                call_command(
                    'migrate', database='user_upgrade', interactive=False, verbosity=0
                )
            except RuntimeError as error:
                assert 'autonomous migration transition' in str(error)
            else:
                raise AssertionError(
                    'Missing autonomous marker must block before the user switch.'
                )
            assert 'users_user' not in database.introspection.table_names()
            assert state.get_model('employers', 'EmployerImport').objects.using(
                'user_upgrade'
            ).get().data == {'description': 'Preserved fictional offer'}
            recorder.record_applied('employers', '0001_autonomous_schema')
            LegacyUser = state.get_model('auth', 'User')
            legacy_user = LegacyUser._base_manager.using('user_upgrade').create(
                username='operator@example.invalid', password='!'
            )
            try:
                call_command(
                    'migrate', database='user_upgrade', interactive=False, verbosity=0
                )
            except RuntimeError as error:
                assert 'explicit kind assignment' in str(error)
            else:
                raise AssertionError(
                    'An account without a known kind must block migration.'
                )
            assert (
                LegacyUser._base_manager.using('user_upgrade')
                .filter(pk=legacy_user.pk)
                .exists()
            )
            LegacyUser._base_manager.using('user_upgrade').filter(
                pk=legacy_user.pk
            ).delete()
            duplicate = (
                state.get_model('employers', 'EmployerIdentity')
                .objects.using('user_upgrade')
                .create(email='CONTACT@example.invalid')
            )
            try:
                call_command(
                    'migrate', database='user_upgrade', interactive=False, verbosity=0
                )
            except RuntimeError as error:
                assert 'Conflicting identity emails' in str(error)
            else:
                raise AssertionError(
                    'Case-insensitive collisions must block migration.'
                )
            assert (
                state.get_model('employers', 'EmployerIdentity')
                .objects.using('user_upgrade')
                .count()
                == 2
            )
            state.get_model('employers', 'EmployerIdentity').objects.using(
                'user_upgrade'
            ).filter(pk=duplicate.pk).delete()
            call_command(
                'migrate', database='user_upgrade', interactive=False, verbosity=0
            )
            from eures_beta.users.models import User
            from eures_beta.employers.models import (
                JobOffer,
                CompanyMembership,
                EmployerSearchOperation,
                EmployerSearchEvent,
            )

            user = User.objects.using('user_upgrade').get(
                email='contact@example.invalid'
            )
            assert user.kind == 'employer' and not user.has_usable_password()
            assert (
                CompanyMembership.objects.using('user_upgrade').get().person_id
                == user.pk
            )
            assert JobOffer.objects.using('user_upgrade').get().created_by_id == user.pk
            assert JobOffer.objects.using('user_upgrade').get().data == {
                'description': 'Preserved fictional offer'
            }
            assert (
                EmployerSearchOperation.objects.using('user_upgrade')
                .get()
                .requested_by_id
                == user.pk
            )
            assert (
                EmployerSearchEvent.objects.using('user_upgrade').get().actor_id
                == user.pk
            )
            tables = database.introspection.table_names()
            assert (
                'auth_user' not in tables and 'journeys_employeridentity' not in tables
            )
            # A second execution must not bootstrap or overwrite migrated users.
            call_command(
                'migrate', database='user_upgrade', interactive=False, verbosity=0
            )
            assert User.objects.using('user_upgrade').count() == 1
            print(
                'Upgrade from legacy schema: four relations and offer data preserved; repeat execution succeeds.'
            )
        finally:
            database.close()
            del connections['user_upgrade']
            del connections.databases['user_upgrade']
            maintenance.execute(
                sql.SQL('DROP DATABASE {}').format(sql.Identifier(name))
            )


if __name__ == '__main__':
    main()
