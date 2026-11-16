"""Rename conversations in place, including PostgreSQL objects and permissions.

Keep 0008 intact: deployed previews can still be adopted and rolled back.
The naming algorithm is frozen here, independent of future Django versions.
"""

import hashlib

from django.db import migrations, models
import django.db.models.deletion

NAMES = (
    ('sharedconversation', 'candidateofferconversation'),
    ('sharedmessage', 'candidateofferconversationmessage'),
)
DISPLAY_NAMES = {
    'sharedconversation': 'shared conversation',
    'sharedmessage': 'shared message',
    'candidateofferconversation': 'candidate offer conversation',
    'candidateofferconversationmessage': 'candidate offer conversation message',
}


def object_name(table, columns, suffix):
    value = '_'.join([table, *columns, suffix])
    if len(value) <= 63:
        return value
    return value[:54] + '_' + hashlib.sha256(value.encode()).hexdigest()[:8]


def rename_objects(apps, schema_editor, reverse=False):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Conversation naming requires PostgreSQL.')
    quote = schema_editor.quote_name
    for old_model, new_model in NAMES:
        # Reverse runs before Django restores the old table and column names.
        model = apps.get_model('matching', new_model)
        table = model._meta.db_table
        target = 'matching_' + (old_model if reverse else new_model)
        with connection.cursor() as cursor:
            objects = connection.introspection.get_constraints(cursor, table)
            plan = []
            for old, details in objects.items():
                columns = details['columns']
                if not columns or any(not isinstance(c, str) for c in columns):
                    raise RuntimeError(f'Unexpected schema expression on {table}.')
                if reverse:
                    columns = [
                        'confirmation_id' if c == 'offer_review_id' else c
                        for c in columns
                    ]
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
                else:
                    raise RuntimeError(f'Unexpected schema object on {table}: {old}.')
                plan.append((kind, old, object_name(target, columns, suffix)))
            # PostgreSQL 18 names NOT NULL constraints; Django introspection
            # does not include them. PostgreSQL 17 simply returns no rows here.
            cursor.execute(
                'SELECT c.conname, a.attname FROM pg_constraint c '
                'JOIN pg_attribute a ON a.attrelid=c.conrelid '
                'AND a.attnum=c.conkey[1] '
                "WHERE c.conrelid=%s::regclass AND c.contype='n'",
                [table],
            )
            for old, column in cursor.fetchall():
                if reverse and column == 'offer_review_id':
                    column = 'confirmation_id'
                plan.append(
                    ('CONSTRAINT', old, object_name(target, [column], 'not_null'))
                )
            if len({new for _, _, new in plan}) != len(plan):
                raise RuntimeError(f'Ambiguous schema objects on {table}.')
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
            cursor.execute(
                'SELECT n.nspname, c.relname FROM pg_class c '
                'JOIN pg_namespace n ON n.oid=c.relnamespace '
                'WHERE c.oid=pg_get_serial_sequence(%s, %s)::regclass',
                [quote(table), 'id'],
            )
            namespace, old = cursor.fetchone()
            new = object_name(target, ['id'], 'seq')
            if old != new:
                schema_editor.execute(
                    f'ALTER SEQUENCE {quote(namespace)}.{quote(old)} RENAME TO {quote(new)}'
                )


def rename_permissions(apps, schema_editor, reverse=False):
    alias = schema_editor.connection.alias
    content_types = apps.get_model('contenttypes', 'ContentType').objects.using(alias)
    permissions = apps.get_model('auth', 'Permission').objects.using(alias)
    for old, new in NAMES:
        if reverse:
            old, new = new, old
        source = content_types.filter(app_label='matching', model=old).first()
        target = content_types.filter(app_label='matching', model=new).first()
        if source and target:
            raise RuntimeError(
                'Conflicting conversation content types; inspect before migrating.'
            )
        content_type = source or target
        if not content_type:
            continue
        if source:
            source.model = new
            source.save(using=alias, update_fields=['model'])
        for action in ('add', 'change', 'delete', 'view'):
            permission = permissions.filter(
                content_type=content_type, codename=f'{action}_{old}'
            ).first()
            if permission:
                permission.codename = f'{action}_{new}'
                permission.name = f'Can {action} {DISPLAY_NAMES[new]}'
                permission.save(using=alias, update_fields=['codename', 'name'])


def forwards(apps, schema_editor):
    rename_objects(apps, schema_editor)
    rename_permissions(apps, schema_editor)


def backwards(apps, schema_editor):
    rename_objects(apps, schema_editor, reverse=True)
    rename_permissions(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0008_sharedconversation_sharedmessage'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.RenameModel('SharedConversation', 'CandidateOfferConversation'),
        migrations.RenameModel('SharedMessage', 'CandidateOfferConversationMessage'),
        migrations.RenameField(
            'candidateofferconversation', 'confirmation', 'offer_review'
        ),
        migrations.AlterField(
            model_name='candidateofferconversation',
            name='offer_review',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='candidate_offer_conversation',
                to='matching.candidateofferreview',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
