from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('candidates', '0007_previewpushsubscription'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PreviewPushSubscription',
            new_name='CandidatePushSubscription',
        ),
    ]
