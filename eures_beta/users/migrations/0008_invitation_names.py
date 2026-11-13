"""Rename existing invitation data, without recreating accounts or tokens."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def rename_metadata(apps, schema_editor, old, new):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    old_type = (
        ContentType.objects.using(alias).filter(app_label='users', model=old).first()
    )
    new_type = (
        ContentType.objects.using(alias).filter(app_label='users', model=new).first()
    )
    if old_type and new_type:
        raise RuntimeError(
            'Conflicting invitation content types; refusing to merge permissions.'
        )
    content_type = old_type or new_type
    if not content_type:
        return
    if old_type:
        ContentType.objects.using(alias).filter(pk=old_type.pk).update(model=new)
    for action in ('add', 'change', 'delete', 'view'):
        Permission.objects.using(alias).filter(
            content_type_id=content_type.pk, codename=f'{action}_{old}'
        ).update(codename=f'{action}_{new}', name=f'Can {action} {new}')


def forward(apps, schema_editor):
    rename_metadata(apps, schema_editor, 'employerinvitation', 'invitation')


def backward(apps, schema_editor):
    rename_metadata(apps, schema_editor, 'invitation', 'employerinvitation')


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0007_user_adviser_organisation'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.RenameModel('EmployerInvitation', 'Invitation'),
        migrations.RenameField('invitation', 'invited_by', 'sender'),
        migrations.RenameField('invitation', 'audience', 'recipient_kind'),
        migrations.RenameField('invitation', 'employer', 'recipient'),
        migrations.RenameField('user', 'adviser_organisation', 'organization_name'),
        migrations.AlterField(
            model_name='invitation',
            name='sender',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='sent_invitations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='recipient',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invitation',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='organization_name',
            field=models.CharField(
                blank=True, db_default='', max_length=150, verbose_name='Organisation'
            ),
        ),
        migrations.RunPython(forward, backward),
    ]
