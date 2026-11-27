"""Follow-up and conclusion histories now live in matching.MatchEvent."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('followup', '0002_domain_table_names'),
        ('matching', '0037_unify_match_events'),
    ]
    operations = [
        migrations.DeleteModel(name='MatchFollowupEvent'),
        migrations.DeleteModel(name='MatchConclusionEvent'),
    ]
