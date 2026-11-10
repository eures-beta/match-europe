"""Local evaluations contain evidence, not copies of contact details."""

from django.db import models
from . import validation


class OfferRequirements(models.Model):
    """Explicit structured supplements for fictional local scenarios only."""

    offer = models.OneToOneField(
        'employers.JobOffer',
        on_delete=models.CASCADE,
        related_name='matching_requirements',
    )
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        validation.requirements(self.data)
        return super().save(*args, **kwargs)


class MatchPair(models.Model):
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
                fields=['candidate', 'offer'], name='matching_unique_pair'
            )
        ]


class MatchEvaluation(models.Model):
    pair = models.ForeignKey(
        MatchPair, on_delete=models.CASCADE, related_name='evaluations'
    )
    fingerprint = models.CharField(max_length=64)
    rules_version = models.CharField(max_length=64)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_evaluation'


class MatchDecision(models.Model):
    pair = models.ForeignKey(
        MatchPair, on_delete=models.CASCADE, related_name='decisions'
    )
    evaluation = models.ForeignKey(MatchEvaluation, on_delete=models.CASCADE)
    value = models.CharField(
        max_length=12, choices=[('retained', 'Retained'), ('refused', 'Refused')]
    )
    # No actor impersonation: this prototype has an explicit local operator only.
    actor = models.CharField(max_length=32, default='local_operator', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_decision'
