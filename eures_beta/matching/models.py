"""Local evaluations contain evidence, not copies of contact details."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
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
    # Preserve the legacy actor for decisions recorded by the operator workflow.
    actor = models.CharField(max_length=32, default='local_operator', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)


class CandidateOfferReview(models.Model):
    """An adviser explicitly chooses an offer for a private candidate review."""

    match = models.OneToOneField(
        CandidateOfferMatch,
        on_delete=models.CASCADE,
        related_name='candidate_offer_review',
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    email_status = models.CharField(
        max_length=12,
        default='pending',
        choices=[
            ('pending', _('Email not sent')),
            ('sending', _('Email sending in progress')),
            ('sent', _('Email accepted by the mail service')),
            ('failed', _('Email could not be sent')),
            ('disabled', _('Email delivery is not configured or enabled')),
        ],
    )
    email_attempted_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    workflow_state = models.CharField(
        max_length=12,
        default='waiting',
        choices=[
            ('waiting', _('Awaiting candidate replies')),
            ('ready', _('Ready for adviser review')),
            ('claimed', _('Being reviewed')),
            ('clarify', _('Additional information requested')),
            ('validated', _('Validated by an adviser')),
            ('refused', _('Closed by an adviser')),
        ],
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='+',
    )
    workflow_version = models.PositiveIntegerField(default=0)
    submitted_fingerprint = models.CharField(max_length=64, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)


class CandidateOfferReviewAction(models.Model):
    """Append-only adviser handling and immutable submitted summaries."""

    review = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='actions'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    action = models.CharField(
        max_length=16,
        choices=[
            ('submitted', _('Replies submitted')),
            ('reopened', _('Review reopened')),
            ('claim', _('Responsibility accepted')),
            ('release', _('Responsibility released')),
            ('takeover', _('Review taken over')),
            ('validated', _('Validated by an adviser')),
            ('clarify', _('Additional information requested')),
            ('refused', _('Closed by an adviser')),
            ('candidate_reply', _('Additional information received')),
        ],
    )
    internal_note = models.TextField(max_length=2000, blank=True)
    public_message = models.TextField(max_length=2000, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    delivery_status = models.CharField(max_length=12, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'version'],
                name='matching_candidateofferreviewaction_version_unique',
            )
        ]


class CandidateProfileReviewPrompt(models.Model):
    """Three distinct current refusals invite review, never infer a new preference."""

    candidate = models.ForeignKey(
        'candidates.CandidateProfile', on_delete=models.CASCADE
    )
    condition_hash = models.CharField(max_length=64)
    profile_updated_at = models.DateTimeField()
    condition = models.JSONField()
    evidence = models.JSONField()
    resolution = models.CharField(max_length=12, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'condition_hash', 'profile_updated_at'],
                name='matching_candidateprofilereviewprompt_condition_unique',
            )
        ]


class CandidateOfferReviewAnswer(models.Model):
    review = models.ForeignKey(
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


class CandidateProfileSharing(models.Model):
    review = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='profile_sharings'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    agreed = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)


class CandidateOfferConversation(models.Model):
    class State(models.TextChoices):
        REQUESTED = 'requested'
        APPROVED = 'approved'
        DECLINED = 'declined'
        OPEN = 'open'

    offer_review = models.OneToOneField(
        CandidateOfferReview,
        on_delete=models.CASCADE,
        related_name='candidate_offer_conversation',
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


class CandidateOfferConversationMessage(models.Model):
    conversation = models.ForeignKey(
        CandidateOfferConversation, on_delete=models.CASCADE, related_name='messages'
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)


class JobOfferSupport(models.Model):
    """Shared adviser support for recruiting against one job offer."""

    job_offer = models.OneToOneField('employers.JobOffer', on_delete=models.CASCADE)
    is_searching = models.BooleanField(default=False)
    follow_up_on = models.DateField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)


class CandidateSupport(models.Model):
    """Shared adviser support for one candidate's job search."""

    candidate_profile = models.OneToOneField(
        'candidates.CandidateProfile', on_delete=models.CASCADE
    )
    is_searching = models.BooleanField(default=False)
    follow_up_on = models.DateField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)
