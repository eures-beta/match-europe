"""Rename the review and its PostgreSQL objects without replacing data."""

from django.db import migrations

OLD_TABLE = 'matching_employerofferconsent'
NEW_TABLE = 'matching_employercandidatereview'


def rename_objects(schema_editor, table, old, new):
    """Frozen naming helper, also covering PostgreSQL 18 NOT NULL names."""
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Review schema renaming requires PostgreSQL.')
    quote = schema_editor.quote_name

    def renamed(name):
        result = name.replace(old, new)
        if len(result) > 63:
            raise RuntimeError(f'Review schema name exceeds PostgreSQL limit: {result}')
        return result

    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass',
            [table],
        )
        for (name,) in cursor.fetchall():
            target = renamed(name)
            if target != name:
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT '
                    f'{quote(name)} TO {quote(target)}'
                )
        # Renaming a primary/unique constraint already renamed its backing index.
        cursor.execute(
            'SELECT c.relname FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid '
            'WHERE i.indrelid = %s::regclass',
            [table],
        )
        for (name,) in cursor.fetchall():
            target = renamed(name)
            if target != name:
                schema_editor.execute(
                    f'ALTER INDEX {quote(name)} RENAME TO {quote(target)}'
                )
        cursor.execute(
            'SELECT c.relname FROM pg_class c '
            "WHERE c.oid = pg_get_serial_sequence(%s, 'id')::regclass",
            [table],
        )
        for (name,) in cursor.fetchall():
            target = renamed(name)
            if target != name:
                schema_editor.execute(
                    f'ALTER SEQUENCE {quote(name)} RENAME TO {quote(target)}'
                )


def forwards(apps, schema_editor):
    rename_objects(schema_editor, NEW_TABLE, OLD_TABLE, NEW_TABLE)


def backwards(apps, schema_editor):
    rename_objects(schema_editor, NEW_TABLE, NEW_TABLE, OLD_TABLE)


class Migration(migrations.Migration):
    dependencies = [('matching', '0025_employer_consent_database_names')]
    operations = [
        migrations.RenameModel('EmployerOfferConsent', 'EmployerCandidateReview'),
        migrations.RunPython(forwards, backwards),
    ]
