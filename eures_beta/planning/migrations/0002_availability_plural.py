from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('planning', '0001_initial')]
    operations = [
        migrations.AlterModelOptions(
            name='staffdailyavailability',
            options={'verbose_name_plural': 'staff daily availabilities'},
        )
    ]
