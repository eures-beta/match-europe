"""Rename follow-up models and PostgreSQL objects in place, with rollback."""

from importlib import import_module

from django.db import migrations, models
import django.db.models.deletion


def rename_objects(schema_editor, *, reverse=False):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Follow-up renaming requires PostgreSQL.')
    quote = schema_editor.quote_name
    object_name = import_module(
        'eures_beta.matching.migrations.0011_harmonize_database_objects'
    ).object_name
    for suffix in ('', 'event'):
        old = f'matching_introductionfollowup{suffix}'
        new = f'matching_matchfollowup{suffix}'
        source, target = (new, old) if reverse else (old, new)
        table = target
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT c.conname, c.contype, ARRAY(SELECT a.attname '
                'FROM unnest(c.conkey) WITH ORDINALITY k(num, position) '
                'JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.num '
                'ORDER BY k.position) FROM pg_constraint c WHERE c.conrelid = %s::regclass',
                [table],
            )
            for name, kind, columns in cursor.fetchall():
                ending = {
                    'p': 'pkey',
                    'u': 'key',
                    'f': 'fk',
                    'c': 'check',
                    'n': 'not_null',
                }[kind]
                renamed = object_name(table, [] if kind == 'p' else columns, ending)
                if renamed != name:
                    schema_editor.execute(
                        f'ALTER TABLE {quote(table)} RENAME CONSTRAINT '
                        f'{quote(name)} TO {quote(renamed)}'
                    )
            objects = connection.introspection.get_constraints(cursor, table)
            for name, detail in objects.items():
                if (
                    not detail['index']
                    or detail['primary_key']
                    or name.startswith(table + '_')
                ):
                    continue
                renamed = object_name(
                    table,
                    detail['columns'],
                    'unique_idx' if detail['unique'] else 'idx',
                )
                if renamed != name:
                    schema_editor.execute(
                        f'ALTER INDEX {quote(name)} RENAME TO {quote(renamed)}'
                    )
            cursor.execute(
                "SELECT c.relname FROM pg_class c WHERE c.oid = pg_get_serial_sequence(%s, 'id')::regclass",
                [table],
            )
            for (name,) in cursor.fetchall():
                renamed = table + '_id_seq'
                if renamed != name:
                    schema_editor.execute(
                        f'ALTER SEQUENCE {quote(name)} RENAME TO {quote(renamed)}'
                    )
            schema_editor.execute(
                f'ALTER TRIGGER {quote(source + "_adviser_guard")} ON {quote(table)} '
                f'RENAME TO {quote(target + "_adviser_guard")}'
            )
            schema_editor.execute(
                f'ALTER FUNCTION {quote(source + "_check_adviser")}() '
                f'RENAME TO {quote(target + "_check_adviser")}'
            )


def forwards(apps, schema_editor):
    rename_objects(schema_editor)


def backwards(apps, schema_editor):
    rename_objects(schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [('matching', '0031_alter_introductionfollowup_review')]
    operations = [
        # Reverse normalization must follow Django's reverse FK recreation.
        migrations.RunPython(migrations.RunPython.noop, backwards),
        migrations.RenameModel('IntroductionFollowup', 'MatchFollowup'),
        migrations.RenameModel('IntroductionFollowupEvent', 'MatchFollowupEvent'),
        migrations.AlterField(
            'matchfollowup',
            'review',
            models.OneToOneField(
                'matching.candidateofferreview',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='match_followup',
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
