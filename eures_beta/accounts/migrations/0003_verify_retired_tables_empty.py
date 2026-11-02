"""Refuse schema removal if any non-scenario data remains."""

from django.db import migrations

LEGACY_MODELS = (
    ('accounts', 'Profile'),
    ('accounts', 'AccessToken'),
    ('accounts', 'Event'),
    ('candidates', 'Candidate'),
    ('offers', 'Offer'),
    ('offers', 'Question'),
    ('matching', 'Match'),
    ('matching', 'Answer'),
    ('conversations', 'Conversation'),
    ('conversations', 'Message'),
    ('documents', 'Document'),
    ('notifications', 'Notification'),
)


def verify_empty(apps, schema_editor):
    for label, name in LEGACY_MODELS:
        if (
            apps.get_model(label, name)
            .objects.using(schema_editor.connection.alias)
            .exists()
        ):
            raise RuntimeError(
                f'Legacy {label}.{name} still contains non-scenario data; refusing table removal.'
            )


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_remove_legacy_demo_accounts')]
    operations = [migrations.RunPython(verify_empty, migrations.RunPython.noop)]
