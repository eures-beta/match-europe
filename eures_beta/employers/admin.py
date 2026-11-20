"""Read-only business data for superadministrators."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from eures_beta.users.admin_base import ReadOnlyAdmin, json_display, redact
from .models import (
    EmployerProfile,
    JobOffer,
)


@admin.register(JobOffer)
class JobOfferAdmin(ReadOnlyAdmin):
    list_display = (
        'id',
        'employer',
        'source_kind',
        'revision',
        'created',
        'updated',
    )
    list_filter = ('source_kind',)
    search_fields = ('data__companyName', 'employer__email')
    list_select_related = ('employer', 'adviser', 'duplicated_from')
    ordering = ('-created',)
    replacements = {
        'data': 'safe_data',
        'contact': 'safe_contact',
        'sandbox_response': 'safe_response',
        'source_url': 'safe_source_url',
    }

    def get_readonly_fields(self, request, obj=None):
        return tuple(
            self.replacements.get(field, field)
            for field in super().get_readonly_fields(request, obj)
        )

    @admin.display(description=_('Data'))
    def safe_data(self, obj):
        return json_display(obj.data)

    @admin.display(description=_('Contact'))
    def safe_contact(self, obj):
        return json_display(obj.contact)

    @admin.display(description=_('External response'))
    def safe_response(self, obj):
        return json_display(obj.sandbox_response)

    @admin.display(description=_('Source URL'))
    def safe_source_url(self, obj):
        return redact(obj.source_url)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(ReadOnlyAdmin):
    list_display = (
        'user',
        'response_coverage',
        'response_time',
        'revision',
        'updated',
    )
    list_filter = ('response_coverage', 'response_time')
    list_select_related = ('user',)
    ordering = ('-updated',)
