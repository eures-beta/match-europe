"""Targeting matching also completes both new domain schemas before post_migrate."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0035_extract_introductions_and_followup'),
        ('introductions', '0003_complete_domain_extraction'),
        ('followup', '0002_domain_table_names'),
    ]
    operations = []
