from django.contrib import admin
from eures_beta.users.admin_base import MetadataOnlyAdmin
from .models import MatchPair, MatchEvaluation, MatchDecision


@admin.register(MatchPair)
class MatchPairAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'decision', 'created_at')
    exclude = ('candidate', 'offer', 'candidate_facts', 'team')


@admin.register(MatchEvaluation)
class MatchEvaluationAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'rules_version', 'created_at')
    exclude = ('pair', 'fingerprint', 'result', 'requested_by')


@admin.register(MatchDecision)
class MatchDecisionAdmin(MetadataOnlyAdmin):
    list_display = ('id', 'value', 'created_at')
    exclude = ('pair', 'evaluation', 'actor', 'decided_by', 'team', 'reason')


from .models import MatchingTeam, TeamMembership, TeamOffer, TeamCandidate


@admin.register(MatchingTeam, TeamMembership, TeamOffer, TeamCandidate)
class TeamMetadataAdmin(MetadataOnlyAdmin):
    list_display = ('id',)

    def get_readonly_fields(self, request, obj=None):
        return ('id',)
