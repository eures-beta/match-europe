"""Normalize PostgreSQL names and enforce adviser authors on new records."""

from django.db import migrations


def normalize(apps, schema_editor):
    quote = schema_editor.quote_name
    for model in ('IntroductionFollowup', 'IntroductionFollowupEvent'):
        table = apps.get_model('matching', model)._meta.db_table
        with schema_editor.connection.cursor() as cursor:
            objects = schema_editor.connection.introspection.get_constraints(
                cursor, table
            )
        for old, details in objects.items():
            if old.startswith(table + '_'):
                continue
            if details['foreign_key']:
                suffix, kind = 'fk', 'CONSTRAINT'
            elif details['index']:
                suffix, kind = ('unique_idx' if details['unique'] else 'idx'), 'INDEX'
            else:
                raise RuntimeError('Unexpected follow-up schema object')
            new = '_'.join([table, *details['columns'], suffix])
            if len(new) > 63:
                raise RuntimeError('Follow-up schema name too long')
            if kind == 'CONSTRAINT':
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                )
            else:
                schema_editor.execute(
                    f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                )


def guards():
    forward, backward = [], []
    for table, column in (
        ('matching_introductionfollowup', 'updated_by_adviser_id'),
        ('matching_introductionfollowupevent', 'actor_id'),
    ):
        forward.append(f"""
            CREATE FUNCTION {table}_check_adviser() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.{column} AND kind='adviser') THEN
                    RAISE EXCEPTION 'Follow-up author must be an adviser' USING ERRCODE='23514';
                END IF;
                RETURN NEW;
            END $$;
            CREATE TRIGGER {table}_adviser_guard BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {table}_check_adviser();
        """)
        backward.append(
            f'DROP TRIGGER {table}_adviser_guard ON {table}; DROP FUNCTION {table}_check_adviser();'
        )
    return '\n'.join(forward), '\n'.join(backward)


class Migration(migrations.Migration):
    dependencies = [('matching', '0026_introductionfollowup_introductionfollowupevent')]
    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
        migrations.RunSQL(*guards()),
    ]
