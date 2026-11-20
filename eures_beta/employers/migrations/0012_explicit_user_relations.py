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


MAPPINGS = [('employers', 'JobOffer', 'created_by', 'employer')]
ROLES = {'employer': 'employer'}


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
    dependencies = [('employers', '0009_remove_company_workspaces')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE employers_joboffer RENAME COLUMN created_by_id TO employer_id',
                    'ALTER TABLE employers_joboffer RENAME COLUMN employer_id TO created_by_id',
                )
            ],
            state_operations=[
                migrations.RenameField('joboffer', 'created_by', 'employer')
            ],
        ),
        migrations.AlterField(
            'joboffer',
            'employer',
            models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={"kind": 'employer'},
                null=True,
                blank=True,
                related_name='owned_job_offers',
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RunSQL(
            "CREATE OR REPLACE FUNCTION employers_joboffer_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\nIF NEW.employer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.employer_id AND kind='employer') THEN RAISE EXCEPTION 'JobOffer owner must be an employer' USING ERRCODE='23514'; END IF;\nIF NEW.adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'JobOffer adviser must be an adviser' USING ERRCODE='23514'; END IF;\nIF NEW.contact ? 'email' THEN RAISE EXCEPTION 'Employer email belongs only to User' USING ERRCODE='23514'; END IF;\nRETURN NEW; END; $$;",
            "CREATE OR REPLACE FUNCTION employers_joboffer_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\nIF NEW.created_by_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.created_by_id AND kind='employer') THEN RAISE EXCEPTION 'JobOffer owner must be an employer' USING ERRCODE='23514'; END IF;\nIF NEW.adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'JobOffer adviser must be an adviser' USING ERRCODE='23514'; END IF;\nIF NEW.contact ? 'email' THEN RAISE EXCEPTION 'Employer email belongs only to User' USING ERRCODE='23514'; END IF;\nRETURN NEW; END; $$;",
        ),
    ]
