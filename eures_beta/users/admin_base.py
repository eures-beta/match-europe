"""Read-only inspection, with explicit secret-field exclusions."""

import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html

SECRET_KEY = re.compile(
    r'password|secret|token|sesame|invitation|authorization|cookie|session|api.?key|nonce|digest',
    re.I,
)


def redact(value):
    if isinstance(value, dict):
        return {
            key: '[redacted]' if SECRET_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str) and value.startswith(('http://', 'https://')):
        try:
            parsed = urlsplit(value)
            if parsed.username or parsed.password:
                return '[redacted]'
            query = [
                (key, '[redacted]' if SECRET_KEY.search(key) else item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            ]
            return urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), '')
            )
        except ValueError:
            return '[redacted]'
    return value


class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None
    change_form_template = 'admin/read_only_change_form.html'
    list_per_page = 50
    exclude = ('password', 'session_key', 'session_data', 'nonce', 'digest')

    def allowed(self, request):
        user = request.user
        return user.is_active and user.is_staff and user.is_superuser

    def has_module_permission(self, request):
        return self.allowed(request)

    def has_view_permission(self, request, obj=None):
        return self.allowed(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}

    def get_readonly_fields(self, request, obj=None):
        return tuple(
            field.name
            for field in (*self.model._meta.fields, *self.model._meta.many_to_many)
            if field.name not in self.exclude
        )

    def get_fields(self, request, obj=None):
        # Do not let ModelAdmin append original JSON fields beside safe displays.
        return self.get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change):
        raise PermissionDenied

    def save_related(self, request, form, formsets, change):
        raise PermissionDenied

    def delete_model(self, request, obj):
        raise PermissionDenied

    def delete_queryset(self, request, queryset):
        raise PermissionDenied

    def history_view(self, request, object_id, extra_context=None):
        # Old change messages are not guaranteed to have been redacted.
        raise PermissionDenied


class MetadataOnlyAdmin(ReadOnlyAdmin):
    """No object links or detail views for records with secret identifiers/repr."""

    list_display_links = None

    def has_view_permission(self, request, obj=None):
        return obj is None and self.allowed(request)


def json_display(value):
    return format_html(
        '<pre>{}</pre>', json.dumps(redact(value), indent=2, ensure_ascii=False)
    )
