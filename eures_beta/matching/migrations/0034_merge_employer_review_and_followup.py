"""Join the independently published employer-review and matching-followup histories."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0027_employer_review_requested_by_adviser'),
        ('matching', '0033_remove_match_followup_review'),
    ]
    operations = []
