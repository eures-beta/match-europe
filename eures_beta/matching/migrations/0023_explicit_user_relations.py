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


MAPPINGS = [
    ('matching', 'CandidateOfferReview', 'assigned_to', 'assigned_to_adviser'),
    ('matching', 'JobOfferSupport', 'updated_by', 'updated_by_adviser'),
    ('matching', 'CandidateSupport', 'updated_by', 'updated_by_adviser'),
]
ROLES = {'assigned_to_adviser': 'adviser', 'updated_by_adviser': 'adviser'}


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
    dependencies = [('matching', '0022_explicit_author_roles')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE matching_candidateofferreview RENAME COLUMN assigned_to_id TO assigned_to_adviser_id',
                    'ALTER TABLE matching_candidateofferreview RENAME COLUMN assigned_to_adviser_id TO assigned_to_id',
                )
            ],
            state_operations=[
                migrations.RenameField(
                    'candidateofferreview', 'assigned_to', 'assigned_to_adviser'
                )
            ],
        ),
        migrations.AlterField(
            'candidateofferreview',
            'assigned_to_adviser',
            models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={"kind": 'adviser'},
                null=True,
                blank=True,
                related_name='+',
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE matching_joboffersupport RENAME COLUMN updated_by_id TO updated_by_adviser_id',
                    'ALTER TABLE matching_joboffersupport RENAME COLUMN updated_by_adviser_id TO updated_by_id',
                )
            ],
            state_operations=[
                migrations.RenameField(
                    'joboffersupport', 'updated_by', 'updated_by_adviser'
                )
            ],
        ),
        migrations.AlterField(
            'joboffersupport',
            'updated_by_adviser',
            models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={"kind": 'adviser'},
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE matching_candidatesupport RENAME COLUMN updated_by_id TO updated_by_adviser_id',
                    'ALTER TABLE matching_candidatesupport RENAME COLUMN updated_by_adviser_id TO updated_by_id',
                )
            ],
            state_operations=[
                migrations.RenameField(
                    'candidatesupport', 'updated_by', 'updated_by_adviser'
                )
            ],
        ),
        migrations.AlterField(
            'candidatesupport',
            'updated_by_adviser',
            models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={"kind": 'adviser'},
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RunSQL(
            "CREATE FUNCTION matching_candidateofferreview_user_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.assigned_to_adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.assigned_to_adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'Invalid user role for CandidateOfferReview.assigned_to_adviser' USING ERRCODE='23514'; END IF; RETURN NEW; END; $$; CREATE TRIGGER matching_candidateofferreview_user_roles BEFORE INSERT OR UPDATE ON matching_candidateofferreview FOR EACH ROW EXECUTE FUNCTION matching_candidateofferreview_user_roles();\nCREATE FUNCTION matching_joboffersupport_user_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.updated_by_adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.updated_by_adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'Invalid user role for JobOfferSupport.updated_by_adviser' USING ERRCODE='23514'; END IF; RETURN NEW; END; $$; CREATE TRIGGER matching_joboffersupport_user_roles BEFORE INSERT OR UPDATE ON matching_joboffersupport FOR EACH ROW EXECUTE FUNCTION matching_joboffersupport_user_roles();\nCREATE FUNCTION matching_candidatesupport_user_roles() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.updated_by_adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.updated_by_adviser_id AND kind='adviser') THEN RAISE EXCEPTION 'Invalid user role for CandidateSupport.updated_by_adviser' USING ERRCODE='23514'; END IF; RETURN NEW; END; $$; CREATE TRIGGER matching_candidatesupport_user_roles BEFORE INSERT OR UPDATE ON matching_candidatesupport FOR EACH ROW EXECUTE FUNCTION matching_candidatesupport_user_roles();\n",
            'DROP TRIGGER matching_candidateofferreview_user_roles ON matching_candidateofferreview; DROP FUNCTION matching_candidateofferreview_user_roles();\nDROP TRIGGER matching_joboffersupport_user_roles ON matching_joboffersupport; DROP FUNCTION matching_joboffersupport_user_roles();\nDROP TRIGGER matching_candidatesupport_user_roles ON matching_candidatesupport; DROP FUNCTION matching_candidatesupport_user_roles();\n',
        ),
    ]
