"""Rename schema objects in place; never recreate a table or reset a sequence.

This naming algorithm is frozen with this migration, independently of future
Django versions. Historical migrations and their adoption contracts stay intact.
"""

import hashlib

from django.db import migrations

APPS = {'users', 'invitations', 'candidates', 'employers', 'matching', 'skills'}
LEGACY_TABLES = {
    'employers_company': 'journeys_employercompany',
    'employers_companymembership': 'journeys_employermembership',
    'employers_joboffer': 'journeys_employerimport',
    'matching_candidateoffermatch': 'matching_matchpair',
    'matching_matchevaluation': 'matching_evaluation',
    'matching_matchdecision': 'matching_decision',
    'matching_candidateofferreview': 'matching_confirmationrequest',
    'matching_candidateofferreviewanswer': 'matching_confirmationanswer',
    'matching_candidateprofilesharing': 'matching_transmissionagreement',
    'invitations_invitation': 'users_invitation',
    'skills_occupationskillsuggestion': 'occupations_occupationskillsuggestion',
}
LEGACY_COLUMNS = {
    'employers_companymembership': {'user_id': 'person_id'},
    'matching_matchevaluation': {'match_id': 'pair_id'},
    'matching_matchdecision': {'match_id': 'pair_id'},
    'matching_candidateofferreview': {'match_id': 'pair_id'},
    'matching_candidateofferreviewanswer': {'review_id': 'request_id'},
    'matching_candidateprofilesharing': {'review_id': 'request_id'},
}


def object_name(table, columns, suffix):
    value = '_'.join([table, *columns, suffix])
    if len(value) <= 63:
        return value
    return value[:54] + '_' + hashlib.sha256(value.encode()).hexdigest()[:8]


def normalize(apps, schema_editor, *, reverse=False):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Schema naming requires PostgreSQL.')
    quote = schema_editor.quote_name
    for model in apps.get_models(include_auto_created=True):
        if (
            model._meta.app_label not in APPS
            or not model._meta.managed
            or model._meta.proxy
        ):
            continue
        table = model._meta.db_table
        target_table = LEGACY_TABLES.get(table, table) if reverse else table
        column_map = LEGACY_COLUMNS.get(table, {}) if reverse else {}
        declared = {
            item.name for item in (*model._meta.constraints, *model._meta.indexes)
        }
        with connection.cursor() as cursor:
            objects = connection.introspection.get_constraints(cursor, table)
            plan = []
            for old, details in objects.items():
                if old in declared:
                    continue
                columns = details['columns']
                if not columns or any(
                    not isinstance(column, str) for column in columns
                ):
                    raise RuntimeError(
                        f'Unexpected unnamed schema expression on {table}.'
                    )
                columns = [column_map.get(column, column) for column in columns]
                if details['primary_key']:
                    kind, suffix, columns = 'CONSTRAINT', 'pkey', []
                elif details['foreign_key']:
                    kind, suffix = 'CONSTRAINT', 'fk'
                elif details['check']:
                    kind, suffix = 'CONSTRAINT', 'check'
                elif details['unique'] and not details['index']:
                    kind, suffix = 'CONSTRAINT', 'key'
                elif details['index']:
                    kind, suffix = 'INDEX', 'idx'
                    cursor.execute('SELECT pg_get_indexdef(%s::regclass)', [quote(old)])
                    definition = cursor.fetchone()[0]
                    if '_pattern_ops' in definition:
                        suffix = 'like'
                    if details['unique']:
                        suffix = 'unique_idx'
                else:
                    raise RuntimeError(f'Unexpected schema object on {table}: {old}.')
                new = object_name(target_table, columns, suffix)
                plan.append((kind, old, new))
            # Django does not expose PostgreSQL 18 named NOT NULL constraints.
            # PostgreSQL 17 returns no rows for this constraint type.
            cursor.execute(
                'SELECT c.conname, a.attname FROM pg_constraint c '
                'JOIN pg_attribute a ON a.attrelid=c.conrelid '
                'AND a.attnum=c.conkey[1] '
                "WHERE c.conrelid=%s::regclass AND c.contype='n'",
                [quote(table)],
            )
            for old, column in cursor.fetchall():
                new = object_name(
                    target_table, [column_map.get(column, column)], 'not_null'
                )
                plan.append(('CONSTRAINT', old, new))
            targets = [new for _, _, new in plan]
            if len(set(targets)) != len(targets):
                raise RuntimeError(
                    f'Ambiguous schema objects on {table}; nothing is removed.'
                )
            for kind, old, new in plan:
                if old == new:
                    continue
                if kind == 'CONSTRAINT':
                    schema_editor.execute(
                        f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                    )
                else:
                    schema_editor.execute(
                        f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                    )
            for field in model._meta.local_fields:
                cursor.execute(
                    'SELECT n.nspname, c.relname FROM pg_class c '
                    'JOIN pg_namespace n ON n.oid=c.relnamespace '
                    'WHERE c.oid=pg_get_serial_sequence(%s, %s)::regclass',
                    [quote(table), field.column],
                )
                sequence = cursor.fetchone()
                if sequence is None:
                    continue
                namespace, old = sequence
                new = object_name(
                    target_table, [column_map.get(field.column, field.column)], 'seq'
                )
                if old != new:
                    schema_editor.execute(
                        f'ALTER SEQUENCE {quote(namespace)}.{quote(old)} RENAME TO {quote(new)}'
                    )
    for table, old, new in (
        ('users_user', 'users_kind_immutable', 'users_user_kind_immutable'),
        (
            'candidates_candidateprofile',
            'candidates_profile_account_kind',
            'candidates_candidateprofile_account_kind',
        ),
    ):
        if reverse:
            old, new = new, old
        schema_editor.execute(
            f'ALTER TRIGGER {quote(old)} ON {quote(table)} RENAME TO {quote(new)}'
        )
    for old, new in (
        ('users_prevent_kind_change', 'users_user_prevent_kind_change'),
        (
            'candidates_require_candidate_account',
            'candidates_candidateprofile_require_candidate_account',
        ),
    ):
        if reverse:
            old, new = new, old
        schema_editor.execute(f'ALTER FUNCTION {quote(old)}() RENAME TO {quote(new)}')


def forwards(apps, schema_editor):
    normalize(apps, schema_editor)


def backwards(apps, schema_editor):
    normalize(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [('matching', '0010_harmonize_model_names')]
    operations = [migrations.RunPython(forwards, backwards)]
