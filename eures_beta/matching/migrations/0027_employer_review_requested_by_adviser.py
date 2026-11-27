"""Keep the requesting adviser, its column and PostgreSQL names explicit."""

from importlib import import_module

from django.db import migrations

TABLE = 'matching_employercandidatereview'


def normalize(schema_editor, target_column):
    connection = schema_editor.connection
    quote = schema_editor.quote_name
    object_name = import_module(
        'eures_beta.matching.migrations.0011_harmonize_database_objects'
    ).object_name
    with connection.cursor() as cursor:
        objects = connection.introspection.get_constraints(cursor, TABLE)
        for old, details in objects.items():
            if details['columns'] != [target_column]:
                continue
            if details['foreign_key']:
                kind, suffix = 'CONSTRAINT', 'fk'
            elif details['index']:
                kind, suffix = 'INDEX', 'idx'
            else:
                raise RuntimeError(f'Unexpected requesting-adviser object: {old}')
            new = object_name(TABLE, [target_column], suffix)
            if old == new:
                continue
            if kind == 'CONSTRAINT':
                schema_editor.execute(
                    f'ALTER TABLE {quote(TABLE)} RENAME CONSTRAINT '
                    f'{quote(old)} TO {quote(new)}'
                )
            else:
                schema_editor.execute(
                    f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                )
        cursor.execute(
            'SELECT c.conname FROM pg_constraint c '
            'JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey) '
            "WHERE c.conrelid=%s::regclass AND c.contype='n' AND a.attname=%s",
            [TABLE, target_column],
        )
        for (old,) in cursor.fetchall():
            new = object_name(TABLE, [target_column], 'not_null')
            if old != new:
                schema_editor.execute(
                    f'ALTER TABLE {quote(TABLE)} RENAME CONSTRAINT '
                    f'{quote(old)} TO {quote(new)}'
                )


def forwards(apps, schema_editor):
    normalize(schema_editor, 'requested_by_adviser_id')


def backwards(apps, schema_editor):
    normalize(schema_editor, 'adviser_id')


class Migration(migrations.Migration):
    dependencies = [('matching', '0026_rename_employer_candidate_review')]
    operations = [
        migrations.RunPython(migrations.RunPython.noop, backwards),
        migrations.RenameField(
            'employercandidatereview', 'adviser', 'requested_by_adviser'
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
