from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from eures_beta.users.role_validation import validate_user_roles


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


class MatchFollowup(models.Model):
    """Shared adviser planning; closing this record never changes consent."""

    class WaitingFor(models.TextChoices):
        ADVISER = 'adviser', _('Adviser')
        CANDIDATE = 'candidate', _('Candidate')
        EMPLOYER = 'employer', _('Employer')

    class Outcome(models.TextChoices):
        OPEN = 'open', _('In progress')
        HIRED = 'hired', _('Hired')
        STOPPED = 'stopped', _('Recruitment stopped')

    match = models.OneToOneField(
        'matching.CandidateOfferMatch',
        on_delete=models.CASCADE,
        related_name='followup',
    )
    next_action = models.CharField(max_length=500)
    waiting_for = models.CharField(max_length=12, choices=WaitingFor.choices)
    due_on = models.DateField(null=True, blank=True, db_index=True)
    outcome = models.CharField(
        max_length=12, choices=Outcome.choices, default=Outcome.OPEN
    )
    closure_reason = models.CharField(max_length=1000, blank=True)
    version = models.PositiveIntegerField(default=0)
    updated_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'adviser'},
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        validate_user_roles(self, updated_by_adviser='adviser')
        return super().save(*args, **kwargs)


class MatchFollowupEvent(models.Model):
    """Adviser-only audit of plans and explicit email attempts; no login links."""

    followup = models.ForeignKey(
        MatchFollowup, on_delete=models.CASCADE, related_name='events'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'kind': 'adviser'},
    )
    action = models.CharField(
        max_length=12,
        choices=[('plan', _('Follow-up updated')), ('reminder', _('Reminder'))],
    )
    recipient = models.CharField(
        max_length=12, blank=True, choices=MatchFollowup.WaitingFor.choices
    )
    message = models.TextField(max_length=2000, blank=True)
    snapshot = models.JSONField(default=dict)
    delivery_status = models.CharField(
        max_length=12,
        blank=True,
        choices=[
            ('sending', _('Email sending in progress')),
            ('sent', _('Email accepted by the mail service')),
            ('failed', _('Email could not be sent')),
            ('disabled', _('Email delivery is not configured or enabled')),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        validate_user_roles(self, actor='adviser')
        return super().save(*args, **kwargs)


class MatchConclusion(models.Model):
    class State(models.TextChoices):
        REPORTED = 'reported', _('Hiring declared — adviser confirmation needed')
        HIRED = 'hired', _('Closed: hiring confirmed')
        STOPPED = 'stopped', _('Closed without hiring')

    match = models.OneToOneField(
        'matching.CandidateOfferMatch',
        on_delete=models.CASCADE,
        related_name='conclusion',
    )
    state = models.CharField(max_length=12, choices=State.choices)
    declared_by_employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'employer'},
    )
    declared_at = models.DateTimeField(null=True, blank=True)
    confirmed_by_adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='+',
        limit_choices_to={'kind': 'adviser'},
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    start_on = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=1000, blank=True)
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=['reported', 'hired', 'stopped']),
                name='followup_matchconclusion_state_valid',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(state='stopped')
                    | models.Q(
                        declared_by_employer__isnull=False, declared_at__isnull=False
                    )
                ),
                name='followup_matchconclusion_declaration_required',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(state='reported')
                    | models.Q(
                        confirmed_by_adviser__isnull=False, confirmed_at__isnull=False
                    )
                ),
                name='followup_matchconclusion_confirmation_required',
            ),
            models.CheckConstraint(
                condition=(~models.Q(state='stopped') | ~models.Q(reason='')),
                name='followup_matchconclusion_stop_reason_required',
            ),
        ]

    def save(self, *args, **kwargs):
        validate_user_roles(
            self, declared_by_employer='employer', confirmed_by_adviser='adviser'
        )
        return super().save(*args, **kwargs)


class MatchConclusionEvent(models.Model):
    conclusion = models.ForeignKey(
        MatchConclusion, on_delete=models.CASCADE, related_name='events'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(
        max_length=12,
        choices=[
            ('reported', _('Hiring declared')),
            ('hired', _('Hiring confirmed')),
            ('stopped', _('Closed without hiring')),
        ],
    )
    version = models.PositiveIntegerField()
    start_on = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['conclusion', 'version'],
                name='followup_matchconclusionevent_version_unique',
            )
        ]
