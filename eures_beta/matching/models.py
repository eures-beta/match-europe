from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from eures_beta.matching import validation


class CandidateOfferMatch(models.Model):
    candidate = models.ForeignKey(
        'candidates.CandidateProfile', on_delete=models.CASCADE
    )
    offer = models.ForeignKey('employers.JobOffer', on_delete=models.CASCADE)
    candidate_facts = models.JSONField(default=dict)
    decision = models.CharField(
        max_length=12,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('retained', 'Retained'),
            ('refused', 'Refused'),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        validation.candidate_facts(self.candidate_facts)
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'offer'],
                name='matching_candidateoffermatch_candidate_offer_unique',
            )
        ]


class MatchEvaluation(models.Model):
    match = models.ForeignKey(
        CandidateOfferMatch, on_delete=models.CASCADE, related_name='evaluations'
    )
    fingerprint = models.CharField(max_length=64)
    rules_version = models.CharField(max_length=64)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class MatchDecision(models.Model):
    match = models.ForeignKey(
        CandidateOfferMatch, on_delete=models.CASCADE, related_name='decisions'
    )
    evaluation = models.ForeignKey(MatchEvaluation, on_delete=models.CASCADE)
    value = models.CharField(
        max_length=12, choices=[('retained', 'Retained'), ('refused', 'Refused')]
    )
    # NULL is reserved for migrated decisions with an unidentified author.
    by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={'kind': 'adviser'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self._state.adding and self.by_adviser_id is None:
            raise ValidationError({'by_adviser': 'A decision requires an adviser.'})
        return super().save(*args, **kwargs)
