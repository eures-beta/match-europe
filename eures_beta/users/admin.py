"""A narrow account-administration UI; privilege assignments are not editable."""

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import User


class AdviserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.kind = User.Kind.ADVISER

    def save(self, commit=True):
        user = super().save(commit=False)
        user.kind = User.Kind.ADVISER
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m()
        return user


@admin.register(User)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'kind', 'is_active', 'is_staff')
    list_filter = ('kind', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = (
        'kind',
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
        'user_permissions',
        'last_login',
        'date_joined',
    )
    fieldsets = (
        (None, {'fields': ('email', 'kind', 'first_name', 'last_name')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return ((None, {'fields': ('email', 'first_name', 'last_name')}),)
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = AdviserCreationForm
        return super().get_form(request, obj, **kwargs)

    def add_view(self, request, form_url='', extra_context=None):
        context = dict(extra_context or {}, title=_('Add adviser'))
        return super().add_view(request, form_url, context)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset
            if request.user.is_superuser
            else queryset.filter(kind=User.Kind.ADVISER)
        )

    def eligible(self, request):
        user = request.user
        return (
            user.is_active
            and user.is_staff
            and (user.is_superuser or user.kind == User.Kind.ADVISER)
        )

    def has_module_permission(self, request):
        return self.eligible(request) and super().has_module_permission(request)

    def has_add_permission(self, request):
        return self.eligible(request) and super().has_add_permission(request)

    def has_view_permission(self, request, obj=None):
        return self.eligible(request) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self.eligible(request) and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False
