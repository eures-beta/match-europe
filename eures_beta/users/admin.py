"""Inspect accounts and invitation metadata; no account or privilege editing."""

import hashlib
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.utils.translation import gettext_lazy as _
from .admin_base import ReadOnlyAdmin, MetadataOnlyAdmin
from .models import User, EmployerInvitation, LoginRateLimit


@admin.register(User)
class AccountAdmin(ReadOnlyAdmin):
    list_display = ('email', 'kind', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('kind', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    def allowed(self, request):
        user = request.user
        return (
            user.is_active
            and user.is_staff
            and (
                user.is_superuser
                or (user.kind == User.Kind.ADVISER and user.has_perm('users.view_user'))
            )
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset
            if request.user.is_superuser
            else queryset.filter(kind=User.Kind.ADVISER)
        )


@admin.register(EmployerInvitation)
class InvitationAdmin(ReadOnlyAdmin):
    list_display = (
        'email',
        'language',
        'invited_by',
        'created_at',
        'expires_at',
        'accepted_at',
        'email_sent_at',
    )
    list_filter = ('language', 'accepted_at')
    search_fields = ('email', 'invited_by__email')
    list_select_related = ('invited_by',)
    ordering = ('-created_at',)


@admin.register(LoginRateLimit)
class RateLimitAdmin(ReadOnlyAdmin):
    list_display = ('key', 'attempts', 'expires')
    ordering = ('-expires',)


class GroupInspectionAdmin(ReadOnlyAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class PermissionInspectionAdmin(ReadOnlyAdmin):
    list_display = ('name', 'content_type', 'codename')
    list_filter = ('content_type__app_label',)
    search_fields = ('name', 'codename')
    list_select_related = ('content_type',)


class ContentTypeInspectionAdmin(ReadOnlyAdmin):
    list_display = ('app_label', 'model')
    search_fields = ('app_label', 'model')


class SessionInspectionAdmin(MetadataOnlyAdmin):
    list_display = ('reference', 'expire_date')
    ordering = ('-expire_date',)

    @admin.display(description=_('Session reference'))
    def reference(self, obj):
        return hashlib.sha256(obj.session_key.encode()).hexdigest()[:16]


class LogInspectionAdmin(MetadataOnlyAdmin):
    list_display = ('action_time', 'user', 'content_type', 'action_flag')
    list_filter = ('action_flag', 'content_type')
    list_select_related = ('user', 'content_type')
    ordering = ('-action_time',)


def register_framework_models(site):
    # auth.admin registers Group during autodiscovery; replace it only afterwards.
    for model, model_admin in (
        (Group, GroupInspectionAdmin),
        (Permission, PermissionInspectionAdmin),
        (ContentType, ContentTypeInspectionAdmin),
        (Session, SessionInspectionAdmin),
        (LogEntry, LogInspectionAdmin),
    ):
        if site.is_registered(model):
            site.unregister(model)
        site.register(model, model_admin)
