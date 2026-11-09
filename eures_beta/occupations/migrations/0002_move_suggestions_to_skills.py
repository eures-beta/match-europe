from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('occupations', '0001_initial'), ('skills', '0001_initial')]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name='OccupationSkillSuggestion')]
        )
    ]
