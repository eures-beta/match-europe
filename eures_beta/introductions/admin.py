from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import (
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
    EmployerCandidateReview,
)


@admin.register(
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
)
class ConfirmationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(CandidateOfferConversation)
class CandidateOfferConversationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'state')


@admin.register(CandidateOfferConversationMessage)
class CandidateOfferConversationMessageMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(EmployerCandidateReview)
class EmployerCandidateReviewMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'decision', 'created_at', 'decided_at')
