"""Rename the account profile without losing existing answers or admin grants."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rename_metadata(apps, schema_editor, reverse=False):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    old, new = 'employerresponsepractice', 'employerprofile'
    label = 'employer profile'
    if reverse:
        old, new = new, old
        label = 'employer response practice'
    types = ContentType.objects.using(alias).filter(
        app_label='employers', model__in=(old, new)
    )
    if types.count() > 1:
        raise RuntimeError('Conflicting employer profile content types.')
    content_type = types.first()
    if content_type is None:
        return  # Fresh installation: post_migrate creates the final metadata.
    for action in ('add', 'change', 'delete', 'view'):
        Permission.objects.using(alias).filter(
            content_type=content_type, codename=f'{action}_{old}'
        ).update(codename=f'{action}_{new}', name=f'Can {action} {label}')
    content_type.model = new
    content_type.save(using=alias, update_fields=['model'])


def forwards(apps, schema_editor):
    rename_metadata(apps, schema_editor)


def backwards(apps, schema_editor):
    rename_metadata(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [('employers', '0004_employerresponsepractice')]

    operations = [
        migrations.RenameModel('EmployerResponsePractice', 'EmployerProfile'),
        migrations.RenameField('employerprofile', 'employer', 'user'),
        migrations.AlterField(
            model_name='employerprofile',
            name='user',
            field=models.OneToOneField(
                limit_choices_to={'kind': 'employer'},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='employer_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            'employerprofile',
            {
                'verbose_name': 'Employer profile',
                'verbose_name_plural': 'Employer profiles',
            },
        ),
        migrations.RunPython(forwards, backwards),
    ]
