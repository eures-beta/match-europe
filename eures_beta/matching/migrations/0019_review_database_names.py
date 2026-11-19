"""Normalize deferred review constraints in place, after their tables exist."""

import hashlib
from django.db import migrations


def object_name(table, columns, suffix):
    tail = '_'.join([*columns, suffix])
    value = table + '_' + tail
    if len(value) <= 63:
        return value
    return table + '_' + hashlib.sha256(tail.encode()).hexdigest()[:12]


def normalize_names(apps, schema_editor):
    quote = schema_editor.quote_name
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Review schema naming requires PostgreSQL.')
    for model_name in (
        'CandidateOfferReview',
        'CandidateOfferReviewAction',
        'CandidateProfileReviewPrompt',
    ):
        table = apps.get_model('matching', model_name)._meta.db_table
        with connection.cursor() as cursor:
            objects = connection.introspection.get_constraints(cursor, table)
        for old, details in objects.items():
            if old.startswith(table + '_'):
                continue
            if details['foreign_key']:
                suffix, kind = 'fk', 'CONSTRAINT'
            elif details['check']:
                suffix, kind = 'check', 'CONSTRAINT'
            elif details['index']:
                suffix, kind = ('unique_idx' if details['unique'] else 'idx'), 'INDEX'
            else:
                raise RuntimeError(f'Unexpected review schema object: {old}')
            new = object_name(table, details['columns'], suffix)
            if kind == 'CONSTRAINT':
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                )
            else:
                schema_editor.execute(
                    f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                )
        # PostgreSQL 18 exposes named NOT NULL constraints outside Django's introspection.
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT c.conname, a.attname FROM pg_constraint c '
                'JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1] '
                "WHERE c.conrelid=%s::regclass AND c.contype='n'",
                [table],
            )
            for old, column in cursor.fetchall():
                if not old.startswith(table + '_'):
                    new = object_name(table, [column], 'not_null')
                    schema_editor.execute(
                        f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                    )


class Migration(migrations.Migration):
    dependencies = [('matching', '0018_candidateofferreview_assigned_to_and_more')]
    operations = [migrations.RunPython(normalize_names, migrations.RunPython.noop)]
