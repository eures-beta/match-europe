from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from .models import User


class CreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'kind')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user


class ChangeForm(forms.ModelForm):
    class Meta:
        model = User
        exclude = ('password',)


@admin.register(User)
class AccountAdmin(UserAdmin):
    add_form = CreationForm
    form = ChangeForm
    list_display = ('email', 'kind', 'is_active', 'is_staff')
    list_filter = ('kind', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'kind')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
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
    add_fieldsets = (
        (
            None,
            {'fields': ('email', 'kind')},
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        return ('kind',) if obj else ()

    def user_change_password(self, request, id, form_url=''):
        raise PermissionDenied
