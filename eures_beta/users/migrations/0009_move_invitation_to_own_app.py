"""Move migration ownership only: keep the table, rows and permission identities."""

from django.db import migrations


def move_content_type(apps, schema_editor, source, target):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    previous = (
        ContentType.objects.using(alias)
        .filter(app_label=source, model='invitation')
        .first()
    )
    destination = (
        ContentType.objects.using(alias)
        .filter(app_label=target, model='invitation')
        .first()
    )
    if previous and destination:
        raise RuntimeError(
            'Conflicting invitation content types; refusing to merge grants.'
        )
    if previous:
        # Permissions, grants and admin log entries reference the same primary key.
        ContentType.objects.using(alias).filter(pk=previous.pk).update(app_label=target)


def forward(apps, schema_editor):
    move_content_type(apps, schema_editor, 'users', 'invitations')


def backward(apps, schema_editor):
    move_content_type(apps, schema_editor, 'invitations', 'users')


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_invitation_names'),
        ('invitations', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name='Invitation')],
        ),
        migrations.RunPython(forward, backward),
    ]
