"""Explicit metadata-only inspection of personal candidate records."""

from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import CandidateProfile, CandidateRegistration


@admin.register(CandidateProfile)
class CandidateProfileAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at', 'updated_at')


@admin.register(CandidateRegistration)
class CandidateRegistrationAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at', 'expires_at')
