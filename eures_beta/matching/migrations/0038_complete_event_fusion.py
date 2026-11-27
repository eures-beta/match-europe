"""Targeting matching also removes the three copied source journals."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0037_unify_match_events'),
        ('introductions', '0004_remove_review_event'),
        ('followup', '0003_remove_separate_events'),
    ]
    operations = []
