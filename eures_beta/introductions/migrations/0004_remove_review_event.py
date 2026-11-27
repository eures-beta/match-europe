"""The review journal has been copied into matching.MatchEvent."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('introductions', '0003_complete_domain_extraction'),
        ('matching', '0037_unify_match_events'),
    ]
    operations = [migrations.DeleteModel(name='CandidateOfferReviewEvent')]
