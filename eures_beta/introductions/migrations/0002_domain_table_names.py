"""Rename existing tables and schema objects in place, preserving row identities."""

from django.db import migrations
from eures_beta.matching.migrations._domain_transfer import normalize_domain


def forward(apps, schema_editor):
    normalize_domain(apps, schema_editor, 'introductions')


def backward(apps, schema_editor):
    normalize_domain(apps, schema_editor, 'introductions', reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('introductions', '0001_initial'),
        ('matching', '0035_extract_introductions_and_followup'),
    ]
    operations = [
        migrations.AlterModelTable(name='candidateofferreview', table=None),
        migrations.AlterModelTable(name='candidateofferreviewevent', table=None),
        migrations.AlterModelTable(name='candidateofferreviewanswer', table=None),
        migrations.AlterModelTable(name='candidateprofilesharing', table=None),
        migrations.AlterModelTable(name='candidateofferconversation', table=None),
        migrations.AlterModelTable(
            name='candidateofferconversationmessage', table=None
        ),
        migrations.AlterModelTable(name='employercandidatereview', table=None),
        migrations.RunPython(forward, backward),
    ]
