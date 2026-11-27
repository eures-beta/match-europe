"""Rename existing tables and schema objects in place, preserving row identities."""

from django.db import migrations
from eures_beta.matching.migrations._domain_transfer import normalize_domain


def forward(apps, schema_editor):
    normalize_domain(apps, schema_editor, 'followup')


def backward(apps, schema_editor):
    normalize_domain(apps, schema_editor, 'followup', reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('followup', '0001_initial'),
        ('matching', '0035_extract_introductions_and_followup'),
        ('introductions', '0002_domain_table_names'),
    ]
    operations = [
        migrations.AlterModelTable(name='joboffersupport', table=None),
        migrations.AlterModelTable(name='candidatesupport', table=None),
        migrations.AlterModelTable(name='matchfollowup', table=None),
        migrations.AlterModelTable(name='matchfollowupevent', table=None),
        migrations.AlterModelTable(name='matchconclusion', table=None),
        migrations.AlterModelTable(name='matchconclusionevent', table=None),
        migrations.RunPython(forward, backward),
    ]
