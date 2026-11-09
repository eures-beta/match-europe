from django.contrib import admin
from eures_beta.users.admin_base import ReadOnlyAdmin
from .models import OccupationSkillSuggestion


@admin.register(OccupationSkillSuggestion)
class OccupationSkillSuggestionAdmin(ReadOnlyAdmin):
    list_display = (
        'occupation_uri',
        'source_version',
        'method',
        'status',
        'updated_at',
    )
    exclude = (*ReadOnlyAdmin.exclude, 'lease')
