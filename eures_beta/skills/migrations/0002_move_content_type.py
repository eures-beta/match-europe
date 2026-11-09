from django.db import migrations


def move(apps, schema_editor, source, target):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    records = ContentType.objects.using(schema_editor.connection.alias)
    old = records.filter(app_label=source, model='occupationskillsuggestion').first()
    if old:
        if records.filter(app_label=target, model=old.model).exists():
            raise RuntimeError(
                'Conflicting suggestion content types; reconcile before migration.'
            )
        old.app_label = target
        old.save(using=schema_editor.connection.alias, update_fields=['app_label'])


def forwards(apps, schema_editor):
    move(apps, schema_editor, 'occupations', 'skills')


def backwards(apps, schema_editor):
    move(apps, schema_editor, 'skills', 'occupations')


class Migration(migrations.Migration):
    dependencies = [
        ('skills', '0001_initial'),
        ('occupations', '0002_move_suggestions_to_skills'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
