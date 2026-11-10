"""Move explicit requirements to their offer before removing the redundant table."""

from django.db import migrations


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    # The retired prototype also used matching.0001_initial. Its recorder row
    # survives retirement, so Django may skip our new initial schema entirely.
    # Only bootstrap an entirely absent schema; never guess at a partial one.
    models = [
        apps.get_model('matching', name)
        for name in (
            'MatchPair',
            'MatchEvaluation',
            'MatchDecision',
            'OfferRequirements',
        )
    ]
    tables = set(schema_editor.connection.introspection.table_names())
    present = {model._meta.db_table for model in models} & tables
    if not present:
        for model in models:
            schema_editor.create_model(model)
    elif len(present) != len(models):
        raise RuntimeError('Partial matching schema: inspect before migrating.')
    Requirements = apps.get_model('matching', 'OfferRequirements')
    Offer = apps.get_model('employers', 'JobOffer')
    for row in Requirements.objects.using(alias).iterator():
        offer = Offer.objects.using(alias).get(pk=row.offer_id)
        if offer.structured_requirements and offer.structured_requirements != row.data:
            raise RuntimeError('Conflicting requirements: inspect before migrating.')
        Offer.objects.using(alias).filter(pk=row.offer_id).update(
            structured_requirements=row.data
        )


def backwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    Requirements = apps.get_model('matching', 'OfferRequirements')
    Offer = apps.get_model('employers', 'JobOffer')
    for offer in (
        Offer.objects.using(alias).exclude(structured_requirements={}).iterator()
    ):
        Requirements.objects.using(alias).create(
            offer_id=offer.pk, data=offer.structured_requirements
        )


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0003_rename_match_decision'),
        ('employers', '0006_joboffer_structured_requirements'),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.DeleteModel(name='OfferRequirements'),
    ]
