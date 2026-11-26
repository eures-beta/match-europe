from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import (
    EmployerCandidateReview,
    MatchConclusion,
    MatchConclusionEvent,
    IntroductionFollowup,
    IntroductionFollowupEvent,
    CandidateSupport,
    JobOfferSupport,
    CandidateOfferMatch,
    MatchEvaluation,
    MatchDecision,
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
    CandidateOfferConversation,
    CandidateOfferConversationMessage,
    CandidateOfferReviewEvent,
)


@admin.register(MatchConclusion, MatchConclusionEvent)
class MatchConclusionMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


@admin.register(IntroductionFollowup, IntroductionFollowupEvent)
class FollowupMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)


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
    exclude = ('match', 'evaluation', 'by_adviser')


@admin.register(
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
    CandidateOfferReviewEvent,
)
class ConfirmationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(CandidateOfferConversation)
class CandidateOfferConversationMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'state')


@admin.register(CandidateOfferConversationMessage)
class CandidateOfferConversationMessageMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'created_at')


@admin.register(JobOfferSupport, CandidateSupport)
class SupportAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'is_searching', 'follow_up_on', 'updated_at')


@admin.register(EmployerCandidateReview)
class EmployerCandidateReviewMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'decision', 'created_at', 'decided_at')
