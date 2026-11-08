"""Local evaluations contain evidence, not copies of contact details."""

from django.db import models
from django.conf import settings
from . import validation


class MatchingTeam(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)


class TeamMembership(models.Model):
    team = models.ForeignKey(MatchingTeam, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    can_decide = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'user'], name='matching_unique_member'
            )
        ]


class TeamOffer(models.Model):
    team = models.ForeignKey(MatchingTeam, on_delete=models.PROTECT)
    offer = models.OneToOneField('employers.JobOffer', on_delete=models.CASCADE)


class TeamCandidate(models.Model):
    team = models.ForeignKey(MatchingTeam, on_delete=models.CASCADE)
    candidate = models.ForeignKey(
        'candidates.CandidateProfile', on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'candidate'], name='matching_unique_candidate_access'
            )
        ]


class MatchPair(models.Model):
    team = models.ForeignKey(
        MatchingTeam, null=True, blank=True, on_delete=models.PROTECT
    )
    source = models.CharField(
        max_length=12,
        default='calculated',
        choices=[('calculated', 'Calculated'), ('manual', 'Manual')],
    )
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
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    request_mode = models.CharField(
        max_length=12,
        default='calculated',
        choices=[('calculated', 'Calculated'), ('manual', 'Manual')],
    )
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
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    team = models.ForeignKey(
        MatchingTeam, null=True, blank=True, on_delete=models.PROTECT
    )
    manual = models.BooleanField(default=False)
    reason = models.TextField(max_length=2000, blank=True)
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

class ConfirmationRequest(models.Model):
    """An adviser explicitly chooses an offer to discuss; never an invitation email."""

    pair = models.OneToOneField(
        MatchPair, on_delete=models.CASCADE, related_name='confirmation_request'
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class ConfirmationAnswer(models.Model):
    request = models.ForeignKey(
        ConfirmationRequest, on_delete=models.CASCADE, related_name='answers'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    question_key = models.CharField(max_length=250)
    fingerprint = models.CharField(max_length=64)
    presented = models.JSONField()
    value = models.CharField(
        max_length=12,
        choices=[
            ('yes', 'Yes'),
            ('conditional', 'Under conditions'),
            ('no', 'Not for this offer'),
            ('changed', 'My situation changed'),
            ('clarify', 'More details needed'),
        ],
    )
    detail = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TransmissionAgreement(models.Model):
    request = models.ForeignKey(
        ConfirmationRequest, on_delete=models.CASCADE, related_name='agreements'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    agreed = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
