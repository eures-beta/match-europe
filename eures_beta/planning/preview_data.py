"""Fictional availability, preserving any previous manual changes."""

from datetime import date
from .models import StaffDailyAvailability


def seed_availability(user):
    StaffDailyAvailability.objects.get_or_create(
        user=user, day=date(2026, 11, 23), defaults={'present': True}
    )
