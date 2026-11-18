"""Keep automatically shortened foreign keys consistent with the table name."""

from django.db import migrations


def normalize_names(apps, schema_editor):
    model = apps.get_model('matching', 'AdviserSearchFollowUp')
    table = model._meta.db_table
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table
        )
        for old, details in constraints.items():
            if old.startswith(table + '_'):
                continue
            if details['foreign_key']:
                suffix, kind = 'fk', 'CONSTRAINT'
            elif details['index']:
                suffix = 'unique_idx' if details['unique'] else 'idx'
                kind = 'INDEX'
            else:
                raise RuntimeError(f'Unexpected schema name on {table}: {old}')
            new = '_'.join([table, *details['columns'], suffix])
            if len(new) > 63:
                raise RuntimeError(f'Search follow-up schema name too long: {new}')
            if kind == 'CONSTRAINT':
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                )
            else:
                schema_editor.execute(
                    f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                )


class Migration(migrations.Migration):
    dependencies = [('matching', '0012_advisersearchfollowup')]
    operations = [migrations.RunPython(normalize_names, migrations.RunPython.noop)]
