from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import (
    AdviserSearchFollowUp,
    CandidateOfferMatch,
    MatchEvaluation,
    MatchDecision,
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
)


@admin.register(CandidateOfferMatch)
class CandidateOfferMatchAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'decision', 'created_at')
    exclude = ('candidate', 'offer', 'candidate_facts')


@admin.register(MatchEvaluation)
class MatchEvaluationAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'rules_version', 'created_at')
    exclude = ('match', 'fingerprint', 'result')


@admin.register(MatchDecision)
class MatchDecisionAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'value', 'created_at')
    exclude = ('match', 'evaluation', 'actor')


@admin.register(
    CandidateOfferReview, CandidateOfferReviewAnswer, CandidateProfileSharing
)
class ConfirmationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(CandidateOfferConversation)
class CandidateOfferConversationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'state')


@admin.register(CandidateOfferConversationMessage)
class CandidateOfferConversationMessageMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(AdviserSearchFollowUp)
class AdviserSearchFollowUpAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'is_searching', 'follow_up_on', 'updated_at')
