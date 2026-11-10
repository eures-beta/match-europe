import uuid
from .offer_requirements import validate_requirements
from .response_practice import RESPONSE_COVERAGE, RESPONSE_TIME
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """A workspace, not a verified legal company registration."""

    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employercompany'
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')


class CompanyMembership(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name='memberships'
    )
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='memberships'
    )
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employermembership'
        verbose_name = _('Company membership')
        verbose_name_plural = _('Company memberships')
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'person'], name='unique_employer_membership'
            )
        ]


class JobOffer(models.Model):
    """Local drafts: private before verification, then attached to an explicit company workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='imports',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='created_imports',
    )
    search_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    duplicated_from = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='duplicates',
        editable=False,
    )

    @property
    def search_write_blocked(self):
        return bool(
            self.search_started_at
            or self.search_operations.filter(
                state__in=['pending', 'uncertain']
            ).exists()
        )

    session_key = models.CharField(max_length=64, db_index=True)
    email = models.EmailField()
    contact = models.JSONField(default=dict)
    adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='advised_imports',
    )
    preparation_agreed_at = models.DateTimeField()
    source_kind = models.CharField(max_length=10)
    source_url = models.URLField(max_length=2048, blank=True)
    data = models.JSONField(default=dict)
    structured_requirements = models.JSONField(
        default=dict, blank=True, validators=[validate_requirements]
    )
    validated_at = models.DateTimeField(null=True)
    initial_sent_at = models.DateTimeField(null=True)
    synced_at = models.DateTimeField(null=True)
    sandbox_response = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        validate_requirements(self.structured_requirements)
        return super().save(*args, **kwargs)

    class Meta:
        db_table = 'journeys_employerimport'
        verbose_name = _('Job offer')
        verbose_name_plural = _('Job offers')


class EmployerEmailLink(models.Model):
    """Single-use local email verification, optionally carrying one explicitly submitted draft."""

    pending_import = models.ForeignKey(
        JobOffer, null=True, blank=True, on_delete=models.PROTECT
    )
    email = models.EmailField()
    digest = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'journeys_employeremaillink'


class EmployerSearchOperation(models.Model):
    """Local simulation only. One durable operation per confirmed offer revision."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(
        JobOffer, on_delete=models.PROTECT, related_name='search_operations'
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    state = models.CharField(
        max_length=12,
        choices=[
            ('pending', 'Pending'),
            ('uncertain', 'Uncertain'),
            ('failed', 'Failed'),
            ('started', 'Started'),
        ],
    )
    scenario = models.CharField(max_length=24, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        db_table = 'journeys_employersearchoperation'
        constraints = [
            models.UniqueConstraint(
                fields=['offer', 'revision'], name='unique_search_offer_revision'
            )
        ]


class EmployerSearchEvent(models.Model):
    operation = models.ForeignKey(
        EmployerSearchOperation, on_delete=models.PROTECT, related_name='events'
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    state = models.CharField(max_length=12)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employersearchevent'


class EmployerProfile(models.Model):
    """Personal employer account profile, independent of the company and colleagues."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='employer_profile',
        limit_choices_to={'kind': 'employer'},
    )
    response_coverage = models.CharField(
        _('Application response coverage'),
        max_length=16,
        choices=RESPONSE_COVERAGE,
    )
    response_time = models.CharField(
        _('Usual first reply timeframe'),
        max_length=24,
        choices=RESPONSE_TIME,
    )
    revision = models.PositiveIntegerField(default=1, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.user_id and self.user.kind != 'employer':
            from django.core.exceptions import ValidationError

            raise ValidationError({'user': _('An employer account is required.')})

    class Meta:
        verbose_name = _('Employer profile')
        verbose_name_plural = _('Employer profiles')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(response_coverage__in=['all', 'selected', 'varies']),
                name='employer_response_coverage_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    response_time__in=[
                        'under_week',
                        'one_two_weeks',
                        'two_weeks_month',
                        'over_month',
                        'variable',
                    ]
                ),
                name='employer_response_time_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1),
                name='employer_response_revision_positive',
            ),
        ]
