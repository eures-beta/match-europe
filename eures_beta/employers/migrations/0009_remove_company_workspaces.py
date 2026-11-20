"""Retire establishment sharing while preserving each offer's explicit owner."""

from django.db import migrations
from django.db.models import Q


def check_offer_owners(apps, schema_editor):
    offers = apps.get_model('employers', 'JobOffer').objects.using(
        schema_editor.connection.alias
    )
    # Do not silently orphan a shared offer or infer ownership from membership/contact.
    invalid_owner = Q(created_by__isnull=True) | ~Q(created_by__kind='employer')
    if offers.filter(company__isnull=False).filter(invalid_owner).exists():
        raise RuntimeError(
            'Cannot retire company workspaces: attached offers require an explicit employer owner.'
        )


def remove_retired_metadata(apps, schema_editor):
    # Cascades only the obsolete permissions/assignments, never users or offers.
    content_types = apps.get_model('contenttypes', 'ContentType')
    content_types.objects.using(schema_editor.connection.alias).filter(
        app_label='employers', model__in=['company', 'companymembership']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('employers', '0008_harmonize_model_names'),
        ('matching', '0020_candidate_offer_review_event'),
    ]

    operations = [
        migrations.RunPython(check_offer_owners, migrations.RunPython.noop),
        migrations.RemoveField(model_name='joboffer', name='company'),
        migrations.DeleteModel(name='CompanyMembership'),
        migrations.DeleteModel(name='Company'),
        migrations.RunPython(remove_retired_metadata, migrations.RunPython.noop),
    ]
