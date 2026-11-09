"""Read-only business data for superadministrators."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from eures_beta.users.admin_base import ReadOnlyAdmin, json_display, redact
from .models import (
    EmployerProfile,
    Company,
    CompanyMembership,
    JobOffer,
    EmployerEmailLink,
    EmployerSearchOperation,
    EmployerSearchEvent,
)


@admin.register(Company)
class CompanyAdmin(ReadOnlyAdmin):
    list_display = ('id', 'name', 'created')
    search_fields = ('name',)
    ordering = ('-created',)


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(ReadOnlyAdmin):
    list_display = ('id', 'company', 'person', 'active', 'created')
    list_filter = ('active',)
    search_fields = ('company__name', 'person__email')
    list_select_related = ('company', 'person')


@admin.register(JobOffer)
class JobOfferAdmin(ReadOnlyAdmin):
    list_display = (
        'id',
        'company',
        'created_by',
        'source_kind',
        'revision',
        'created',
        'updated',
    )
    list_filter = ('source_kind',)
    search_fields = ('email', 'company__name', 'created_by__email')
    list_select_related = ('company', 'created_by', 'adviser', 'duplicated_from')
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


@admin.register(EmployerEmailLink)
class EmailLinkAdmin(ReadOnlyAdmin):
    list_display = ('id', 'email', 'pending_import', 'created', 'expires', 'used')
    list_filter = ('used',)
    search_fields = ('email',)
    list_select_related = ('pending_import',)


@admin.register(EmployerSearchOperation)
class SearchOperationAdmin(ReadOnlyAdmin):
    list_display = (
        'id',
        'offer',
        'requested_by',
        'revision',
        'state',
        'created',
        'resolved_at',
    )
    list_filter = ('state',)
    list_select_related = ('offer', 'requested_by')
    ordering = ('-created',)


@admin.register(EmployerSearchEvent)
class SearchEventAdmin(ReadOnlyAdmin):
    list_display = ('id', 'operation', 'actor', 'state', 'created')
    list_filter = ('state',)
    list_select_related = ('operation', 'actor')
    ordering = ('-created',)


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
