from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import MatchPair, MatchEvaluation, Decision, OfferRequirements


@admin.register(MatchPair)
class MatchPairAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'decision', 'created_at')
    exclude = ('candidate', 'offer', 'candidate_facts')


@admin.register(MatchEvaluation)
class MatchEvaluationAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'rules_version', 'created_at')
    exclude = ('pair', 'fingerprint', 'result')


@admin.register(Decision)
class DecisionAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'value', 'created_at')
    exclude = ('pair', 'evaluation', 'actor')


@admin.register(OfferRequirements)
class OfferRequirementsAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'updated_at')
    exclude = ('offer', 'data')
