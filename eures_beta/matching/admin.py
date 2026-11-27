from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import CandidateOfferMatch, MatchEvaluation, MatchDecision, MatchEvent


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


@admin.register(MatchEvent)
class MatchEventAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'kind', 'action', 'created_at')
