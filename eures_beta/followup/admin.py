from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import (
    MatchConclusion,
    MatchConclusionEvent,
    MatchFollowup,
    MatchFollowupEvent,
    JobOfferSupport,
    CandidateSupport,
)


@admin.register(MatchConclusion, MatchConclusionEvent)
class MatchConclusionMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


@admin.register(MatchFollowup, MatchFollowupEvent)
class FollowupMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


@admin.register(JobOfferSupport, CandidateSupport)
class SupportAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'is_searching', 'follow_up_on', 'updated_at')
