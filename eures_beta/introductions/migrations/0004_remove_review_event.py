"""The review journal has been copied into matching.MatchEvent."""

from importlib import import_module

from django.db import migrations


def copy_review(apps, schema_editor):
    import_module('eures_beta.matching.migrations.0037_unify_match_events').copy_events(
        apps, schema_editor, kinds={'review'}
    )


def restore_review(apps, schema_editor):
    import_module(
        'eures_beta.matching.migrations.0037_unify_match_events'
    ).restore_events(apps, schema_editor, kinds={'review'})


class Migration(migrations.Migration):
    dependencies = [
        ('introductions', '0003_complete_domain_extraction'),
        ('matching', '0037_unify_match_events'),
    ]
    operations = [
        migrations.RunPython(copy_review, restore_review),
        migrations.DeleteModel(name='CandidateOfferReviewEvent'),
    ]
