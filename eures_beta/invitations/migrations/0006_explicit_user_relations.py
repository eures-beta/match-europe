"""Rename role-specific user relations without copying or dropping their data."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def rename_objects(apps, schema_editor, mappings):
    quote = schema_editor.quote_name
    for app, model, old, new in mappings:
        table = apps.get_model(app, model)._meta.db_table
        with schema_editor.connection.cursor() as cursor:
            objects = schema_editor.connection.introspection.get_constraints(
                cursor, table
            )
        for name, item in objects.items():
            if item['columns'] not in ([new + '_id'], [old + '_id']):
                continue
            if item['foreign_key']:
                target, kind = table + '_' + new + '_id_fk', 'CONSTRAINT'
            elif item['index']:
                target, kind = table + '_' + new + '_id_idx', 'INDEX'
            else:
                continue
            if len(target) > 63:
                raise RuntimeError(
                    'Explicit relation schema name exceeds PostgreSQL limit.'
                )
            if name != target:
                if kind == 'INDEX':
                    schema_editor.execute(
                        f'ALTER INDEX {quote(name)} RENAME TO {quote(target)}'
                    )
                else:
                    schema_editor.execute(
                        f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(target)}'
                    )
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                'SELECT c.conname FROM pg_constraint c JOIN pg_attribute a '
                'ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1] '
                "WHERE c.conrelid=%s::regclass AND c.contype='n' AND a.attname IN (%s, %s)",
                [table, new + '_id', old + '_id'],
            )
            names = cursor.fetchall()
        for (name,) in names:
            target = table + '_' + new + '_id_not_null'
            if len(target) > 63:
                # Keep the complete table prefix and a stable suffix.
                import hashlib

                target = (
                    table
                    + '_'
                    + hashlib.sha256((new + '_id_not_null').encode()).hexdigest()[:10]
                )
            if name != target:
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(target)}'
                )


def forwards(apps, schema_editor):
    rename_objects(apps, schema_editor, MAPPINGS)
    for app, model, old, field in MAPPINGS:
        rows = apps.get_model(app, model).objects.using(schema_editor.connection.alias)
        invalid = rows.filter(**{field + '__isnull': False}).exclude(
            **{field + '__kind': ROLES[field]}
        )
        if invalid.exists():
            raise RuntimeError(
                f'{model}.{field}: incompatible user role; migration aborted.'
            )


def backwards(apps, schema_editor):
    rename_objects(
        apps,
        schema_editor,
        [(app, model, new, old) for app, model, old, new in MAPPINGS],
    )


MAPPINGS = [('invitations', 'Invitation', 'sender', 'sender_adviser')]
ROLES = {'sender_adviser': 'adviser'}


def forwards(apps, schema_editor):
    for app, model, old, new in MAPPINGS:
        kind = 'employer' if new == 'employer' else 'adviser'
        rows = apps.get_model(app, model).objects.using(schema_editor.connection.alias)
        if (
            rows.filter(**{new + '__isnull': False})
            .exclude(**{new + '__kind': kind})
            .exists()
        ):
            raise RuntimeError(
                f'{model}.{new}: invalid historical role; migration aborted.'
            )
    rename_objects(apps, schema_editor, MAPPINGS)


def backwards(apps, schema_editor):
    rename_objects(
        apps,
        schema_editor,
        [(app, model, new, old) for app, model, old, new in MAPPINGS],
    )


class Migration(migrations.Migration):
    dependencies = [('invitations', '0005_remove_invitation_company')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE invitations_invitation RENAME COLUMN sender_id TO sender_adviser_id',
                    'ALTER TABLE invitations_invitation RENAME COLUMN sender_adviser_id TO sender_id',
                )
            ],
            state_operations=[
                migrations.RenameField('invitation', 'sender', 'sender_adviser')
            ],
        ),
        migrations.AlterField(
            'invitation',
            'sender_adviser',
            models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={"kind": 'adviser'},
                related_name='sent_invitations',
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RunSQL(
            "CREATE FUNCTION invitations_invitation_user_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.sender_adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.sender_adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'Invalid user role for Invitation.sender_adviser' USING ERRCODE='23514'; END IF; RETURN NEW; END; $$; CREATE TRIGGER invitations_invitation_user_roles BEFORE INSERT OR UPDATE ON invitations_invitation FOR EACH ROW EXECUTE FUNCTION invitations_invitation_user_roles();\n",
            'DROP TRIGGER invitations_invitation_user_roles ON invitations_invitation; DROP FUNCTION invitations_invitation_user_roles();\n',
        ),
    ]
