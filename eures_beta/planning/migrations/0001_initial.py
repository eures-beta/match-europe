from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0012_move_availability_to_planning')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='StaffDailyAvailability',
                    fields=[
                        (
                            'id',
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name='ID',
                            ),
                        ),
                        ('day', models.DateField(db_index=True)),
                        ('present', models.BooleanField()),
                        (
                            'user',
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name='planning_availability',
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        'constraints': [
                            models.UniqueConstraint(
                                fields=('user', 'day'),
                                name='planning_staffdailyavailability_unique_day',
                            )
                        ]
                    },
                )
            ],
        )
    ]
