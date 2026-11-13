"""Local evaluations contain evidence, not copies of contact details."""

from django.conf import settings
from django.db import models
from . import validation


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
        db_table = 'matching_matchpair'
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'offer'], name='matching_unique_pair'
            )
        ]


class MatchEvaluation(models.Model):
    pair = models.ForeignKey(
        CandidateOfferMatch, on_delete=models.CASCADE, related_name='evaluations'
    )
    fingerprint = models.CharField(max_length=64)
    rules_version = models.CharField(max_length=64)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_evaluation'


class MatchDecision(models.Model):
    pair = models.ForeignKey(
        CandidateOfferMatch, on_delete=models.CASCADE, related_name='decisions'
    )
    evaluation = models.ForeignKey(MatchEvaluation, on_delete=models.CASCADE)
    value = models.CharField(
        max_length=12, choices=[('retained', 'Retained'), ('refused', 'Refused')]
    )
    # Preserve the legacy actor for decisions recorded by the operator workflow.
    actor = models.CharField(max_length=32, default='local_operator', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_decision'


class CandidateOfferReview(models.Model):
    """An adviser explicitly chooses an offer to discuss; never an invitation email."""

    pair = models.OneToOneField(
        CandidateOfferMatch,
        on_delete=models.CASCADE,
        related_name='candidate_offer_review',
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_confirmationrequest'


class CandidateOfferReviewAnswer(models.Model):
    request = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='answers'
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
    dialogue = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_confirmationanswer'


class CandidateProfileSharing(models.Model):
    request = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='agreements'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    agreed = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_transmissionagreement'

class SharedConversation(models.Model):
    class State(models.TextChoices):
        REQUESTED = 'requested'
        APPROVED = 'approved'
        DECLINED = 'declined'
        OPEN = 'open'

    confirmation = models.OneToOneField(
        CandidateOfferReview,
        on_delete=models.CASCADE,
        related_name='shared_conversation',
    )
    adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+'
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+'
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+'
    )
    state = models.CharField(
        max_length=12, choices=State.choices, default=State.REQUESTED
    )
    introduction = models.TextField(max_length=2000)
    consent_at = models.DateTimeField(null=True, blank=True)
    adviser_read = models.PositiveBigIntegerField(default=0)
    candidate_read = models.PositiveBigIntegerField(default=0)
    employer_read = models.PositiveBigIntegerField(default=0)


class SharedMessage(models.Model):
    conversation = models.ForeignKey(
        SharedConversation, on_delete=models.CASCADE, related_name='messages'
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
