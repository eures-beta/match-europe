"""Rename model state and metadata, preserving physical tables and grants."""

from django.db import migrations

RENAMES = (('evaluation', 'matchevaluation', 'evaluation', 'match evaluation'),)


def rename_metadata(apps, schema_editor, reverse=False):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    for old, new, old_label, new_label in RENAMES:
        if reverse:
            old, new, old_label, new_label = new, old, new_label, old_label
        types = ContentType.objects.using(alias).filter(
            app_label='matching', model__in=(old, new)
        )
        if types.count() > 1:
            raise RuntimeError(
                'Conflicting matching content types; inspect before migrating.'
            )
        content_type = types.first()
        if content_type is None:
            # Fresh install: post_migrate will create metadata for the new state.
            continue
        for action in ('add', 'change', 'delete', 'view'):
            old_code, new_code = f'{action}_{old}', f'{action}_{new}'
            permissions = Permission.objects.using(alias).filter(
                content_type=content_type, codename__in=(old_code, new_code)
            )
            if permissions.count() > 1:
                raise RuntimeError(
                    'Conflicting matching permissions; inspect before migrating.'
                )
            permission = permissions.first()
            if permission is not None:
                permission.codename = new_code
                permission.name = f'Can {action} {new_label}'
                permission.save(using=alias, update_fields=['codename', 'name'])
        content_type.model = new
        content_type.save(using=alias, update_fields=['model'])


def forwards(apps, schema_editor):
    rename_metadata(apps, schema_editor)


def backwards(apps, schema_editor):
    rename_metadata(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel('Evaluation', 'MatchEvaluation'),
                migrations.AlterModelTable('matchevaluation', 'matching_evaluation'),
            ],
        ),
        migrations.RunPython(forwards, backwards),
    ]
