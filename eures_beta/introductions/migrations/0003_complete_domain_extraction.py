"""An introductions-targeted migration also finishes the linked followup schema."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('introductions', '0002_domain_table_names'),
        ('followup', '0002_domain_table_names'),
    ]
    operations = []
