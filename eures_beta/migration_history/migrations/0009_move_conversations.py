from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('journeys', '0008_employer_search_simulation')]
    operations = [
        # Move ownership in Django's state only: never drop the existing tables.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Message'),
                migrations.DeleteModel(name='Conversation'),
            ],
        ),
    ]
