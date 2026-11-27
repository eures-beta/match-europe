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


class MatchEvent(models.Model):
    """Matching history; private payloads are never a participant-facing feed."""

    class Kind(models.TextChoices):
        REVIEW = 'review', _('Candidate review')
        FOLLOWUP = 'followup', _('Follow-up')
        CONCLUSION = 'conclusion', _('Conclusion')

    match = models.ForeignKey(
        CandidateOfferMatch, on_delete=models.CASCADE, related_name='events'
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    # Review and conclusion retain their independent optimistic-lock counters.
    version = models.PositiveIntegerField(null=True, blank=True)
    # Original identifiers are namespaced by kind when importing existing journals.
    source_id = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
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
            ('plan', _('Follow-up updated')),
            ('reminder', _('Reminder')),
            ('reported', _('Hiring declared')),
            ('hired', _('Hiring confirmed')),
            ('stopped', _('Closed without hiring')),
        ],
    )
    internal_note = models.TextField(max_length=2000, blank=True)
    public_message = models.TextField(max_length=2000, blank=True)
    recipient = models.CharField(
        max_length=12,
        blank=True,
        choices=[
            ('adviser', _('Adviser')),
            ('candidate', _('Candidate')),
            ('employer', _('Employer')),
        ],
    )
    message = models.TextField(max_length=2000, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    delivery_status = models.CharField(
        max_length=12,
        blank=True,
        default='',
        choices=[
            ('pending', _('Email not sent')),
            ('sending', _('Email sending in progress')),
            ('sent', _('Email accepted by the mail service')),
            ('failed', _('Email could not be sent')),
            ('disabled', _('Email delivery is not configured or enabled')),
        ],
    )
    start_on = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['match', 'created_at', 'id'], name='matching_matchevent_history'
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['match', 'kind', 'version'],
                name='matching_matchevent_version_unique',
            ),
            models.UniqueConstraint(
                fields=['kind', 'source_id'], name='matching_matchevent_source_unique'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind='review',
                        version__isnull=False,
                        action__in=[
                            'submitted',
                            'reopened',
                            'claim',
                            'release',
                            'takeover',
                            'validated',
                            'clarify',
                            'refused',
                            'candidate_reply',
                        ],
                    )
                    | models.Q(
                        kind='followup',
                        version__isnull=True,
                        action__in=['plan', 'reminder'],
                    )
                    | models.Q(
                        kind='conclusion',
                        version__isnull=False,
                        action__in=['reported', 'hired', 'stopped'],
                    )
                ),
                name='matching_matchevent_kind_action_valid',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.kind == self.Kind.FOLLOWUP:
            validate_user_roles(self, actor='adviser')
        elif self.kind == self.Kind.CONCLUSION:
            validate_user_roles(
                self, actor='employer' if self.action == 'reported' else 'adviser'
            )
        return super().save(*args, **kwargs)
