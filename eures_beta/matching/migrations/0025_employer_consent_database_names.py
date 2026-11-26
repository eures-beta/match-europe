"""Keep full table prefixes on employer-consent PostgreSQL objects."""

from django.db import migrations


def normalize_names(apps, schema_editor):
    table = apps.get_model('matching', 'EmployerOfferConsent')._meta.db_table
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        objects = schema_editor.connection.introspection.get_constraints(cursor, table)
    for old, details in objects.items():
        if old.startswith(table + '_'):
            continue
        if details['foreign_key']:
            suffix, kind = 'fk', 'CONSTRAINT'
        elif details['index']:
            suffix, kind = ('unique_idx' if details['unique'] else 'idx'), 'INDEX'
        else:
            raise RuntimeError(f'Unexpected employer consent schema object: {old}')
        new = '_'.join([table, *details['columns'], suffix])
        if len(new) > 63:
            raise RuntimeError(
                f'Employer consent schema name exceeds PostgreSQL limit: {new}'
            )
        if kind == 'CONSTRAINT':
            schema_editor.execute(
                f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
            )
        else:
            schema_editor.execute(f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}')


class Migration(migrations.Migration):
    dependencies = [('matching', '0024_employer_offer_consent')]
    # Retaining normalized names on rollback changes no data or model state.
    operations = [migrations.RunPython(normalize_names, migrations.RunPython.noop)]
