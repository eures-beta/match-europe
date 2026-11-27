"""Local evaluations contain evidence, not copies of contact details."""

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from . import validation
from eures_beta.users.role_validation import validate_user_roles


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


class CandidateOfferReview(models.Model):
    """An adviser explicitly chooses an offer for a private candidate review."""

    match = models.OneToOneField(
        CandidateOfferMatch,
        on_delete=models.CASCADE,
        related_name='candidate_offer_review',
    )
    requested_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'kind': 'adviser'},
    )
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
    assigned_to_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'adviser'},
    )
    workflow_version = models.PositiveIntegerField(default=0)
    submitted_fingerprint = models.CharField(max_length=64, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        validate_user_roles(
            self, requested_by_adviser='adviser', assigned_to_adviser='adviser'
        )
        return super().save(*args, **kwargs)


class CandidateOfferReviewEvent(models.Model):
    """Append-only adviser handling and immutable submitted summaries."""

    review = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='events'
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
                name='matching_candidateofferreviewevent_version_unique',
            )
        ]


class CandidateOfferReviewAnswer(models.Model):
    review = models.ForeignKey(
        CandidateOfferReview, on_delete=models.CASCADE, related_name='answers'
    )
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
    updated_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'kind': 'adviser'},
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        validate_user_roles(self, updated_by_adviser='adviser')
        return super().save(*args, **kwargs)


class CandidateSupport(models.Model):
    """Shared adviser support for one candidate's job search."""

    candidate_profile = models.OneToOneField(
        'candidates.CandidateProfile', on_delete=models.CASCADE
    )
    is_searching = models.BooleanField(default=False)
    follow_up_on = models.DateField(null=True, blank=True)
    updated_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'kind': 'adviser'},
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        validate_user_roles(self, updated_by_adviser='adviser')
        return super().save(*args, **kwargs)


class EmployerCandidateReview(models.Model):
    class Decision(models.TextChoices):
        PENDING = 'pending', _('Awaiting employer response')
        ACCEPTED = 'accepted', _('Employer agreed to an introduction')
        DECLINED = 'declined', _('Employer declined')
        CLARIFY = 'clarify', _('Conditions to review with the candidate')

    agreement = models.OneToOneField(CandidateProfileSharing, on_delete=models.CASCADE)
    requested_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'adviser'},
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'employer'},
    )
    questions = models.JSONField(default=list)
    decision = models.CharField(
        max_length=12, choices=Decision.choices, default=Decision.PENDING
    )
    replies = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        validate_user_roles(self, requested_by_adviser='adviser', employer='employer')
        return super().save(*args, **kwargs)
