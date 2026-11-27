from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import (
    MatchConclusion,
    MatchFollowup,
    JobOfferSupport,
    CandidateSupport,
)


@admin.register(MatchConclusion)
class MatchConclusionMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


@admin.register(MatchFollowup)
class FollowupMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


@admin.register(JobOfferSupport, CandidateSupport)
class SupportAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'is_searching', 'follow_up_on', 'updated_at')
