from django.contrib import admin
from eures_beta.users.admin_base import ReadOnlyAdmin
from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(ReadOnlyAdmin):
    list_display = (
        'email',
        'recipient_kind',
        'language',
        'sender',
        'created_at',
        'expires_at',
        'accepted_at',
        'email_sent_at',
    )
    list_filter = ('recipient_kind', 'language', 'accepted_at')
    search_fields = ('email', 'sender__email')
    list_select_related = ('sender',)
    ordering = ('-created_at',)
