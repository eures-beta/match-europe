"""Move availability in place, preserving rows, SQL identities and permissions."""

import hashlib
from django.db import migrations

SOURCE = ('users', 'adviseravailability')
TARGET = ('planning', 'staffdailyavailability')


def object_name(table, columns, suffix):
    tail = '_'.join([*columns, suffix])
    value = table + '_' + tail
    return (
        value
        if len(value) <= 63
        else table + '_' + hashlib.sha256(tail.encode()).hexdigest()[:12]
    )


def move(apps, schema_editor, source, target):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Moving profile review suggestions requires PostgreSQL.')
    quote = schema_editor.quote_name
    before, table = '_'.join(source), '_'.join(target)
    schema_editor.execute(f'ALTER TABLE {quote(before)} RENAME TO {quote(table)}')
    schema_editor.execute(
        f'ALTER TABLE {quote(table)} RENAME COLUMN {quote("adviser_id" if source == SOURCE else "user_id")} TO {quote("user_id" if source == SOURCE else "adviser_id")}'
    )
    # Constraint/index/sequence renames preserve their OIDs and sequence value.
    with connection.cursor() as cursor:
        objects = connection.introspection.get_constraints(cursor, table)
        plan = []
        for old, details in objects.items():
            columns = details['columns']
            if old == before + '_unique_day':
                new, kind = table + '_unique_day', 'CONSTRAINT'
            elif details['primary_key']:
                new, kind = table + '_pkey', 'CONSTRAINT'
            elif details['foreign_key']:
                new, kind = object_name(table, columns, 'fk'), 'CONSTRAINT'
            elif details['check']:
                new, kind = object_name(table, columns, 'check'), 'CONSTRAINT'
            elif details['unique'] and not details['index']:
                new, kind = object_name(table, columns, 'key'), 'CONSTRAINT'
            elif details['index']:
                suffix = 'unique_idx' if details['unique'] else 'idx'
                new, kind = object_name(table, columns, suffix), 'INDEX'
            else:
                raise RuntimeError(f'Unexpected suggestion schema object: {old}')
            plan.append((kind, old, new))
        if len({new for _, _, new in plan}) != len(plan):
            raise RuntimeError('Ambiguous suggestion schema names; nothing is removed.')
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
        # PostgreSQL 18 NOT NULL names are not exposed by Django introspection.
        cursor.execute(
            'SELECT c.conname, a.attname FROM pg_constraint c '
            'JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1] '
            "WHERE c.conrelid=%s::regclass AND c.contype='n'",
            [table],
        )
        for old, column in cursor.fetchall():
            new = object_name(table, [column], 'not_null')
            if old != new:
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                )
        cursor.execute(
            'SELECT pg_get_serial_sequence(%s, %s)::regclass::oid', [table, 'id']
        )
        sequence_oid = cursor.fetchone()[0]
        cursor.execute(
            'SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=%s',
            [sequence_oid],
        )
        namespace, old = cursor.fetchone()
        new = table + '_id_seq'
        if old != new:
            schema_editor.execute(
                f'ALTER SEQUENCE {quote(namespace)}.{quote(old)} RENAME TO {quote(new)}'
            )
    ContentType = apps.get_model('contenttypes', 'ContentType')
    content_type = (
        ContentType.objects.using(connection.alias)
        .filter(app_label=source[0], model=source[1])
        .first()
    )
    if (
        content_type
        and ContentType.objects.using(connection.alias)
        .filter(app_label=target[0], model=target[1])
        .exists()
    ):
        raise RuntimeError(
            'Conflicting planning content types; refusing to merge grants.'
        )
    if content_type:
        # Preserve generic references, permission IDs and group/user assignments.
        Permission = apps.get_model('auth', 'Permission')
        label = (
            'staff daily availability' if target == TARGET else 'adviser availability'
        )
        for verb in ('add', 'change', 'delete', 'view'):
            Permission.objects.using(connection.alias).filter(
                content_type_id=content_type.pk, codename=f'{verb}_{source[1]}'
            ).update(
                codename=f'{verb}_{target[1]}',
                name=f'Can {verb} {label}',
            )
        ContentType.objects.using(connection.alias).filter(pk=content_type.pk).update(
            app_label=target[0], model=target[1]
        )


def forwards(apps, schema_editor):
    move(apps, schema_editor, SOURCE, TARGET)


def backwards(apps, schema_editor):
    move(apps, schema_editor, TARGET, SOURCE)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0011_adviseravailability'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, backwards)],
            state_operations=[migrations.DeleteModel(name='AdviserAvailability')],
        ),
    ]
