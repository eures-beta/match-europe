from django.contrib import admin
from eures_beta.users.admin_base import ReadOnlyAdmin
from .models import StaffDailyAvailability


@admin.register(StaffDailyAvailability)
class StaffDailyAvailabilityAdmin(ReadOnlyAdmin):
    list_display = ('user', 'day', 'present')
    list_filter = ('present', 'day')
    list_select_related = ('user',)
    ordering = ('-day', 'user_id')
