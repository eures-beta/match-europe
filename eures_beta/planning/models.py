from django.conf import settings
from django.db import models


class StaffDailyAvailability(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='planning_availability',
    )
    day = models.DateField(db_index=True)
    present = models.BooleanField()

    class Meta:
        verbose_name_plural = 'staff daily availabilities'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'day'],
                name='planning_staffdailyavailability_unique_day',
            )
        ]
