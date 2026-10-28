import uuid
from django.conf import settings
from django.db import models


class EmployerIdentity(models.Model):
    """Individual identity established by the local email verification flow."""

    email = models.EmailField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employeridentity'


class EmployerCompany(models.Model):
    """A workspace, not a verified legal company registration."""

    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employercompany'


class EmployerMembership(models.Model):
    company = models.ForeignKey(
        EmployerCompany, on_delete=models.PROTECT, related_name='memberships'
    )
    person = models.ForeignKey(
        EmployerIdentity, on_delete=models.PROTECT, related_name='memberships'
    )
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employermembership'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'person'], name='unique_employer_membership'
            )
        ]


class EmployerImport(models.Model):
    """Local drafts: private before verification, then attached to an explicit company workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        EmployerCompany,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='imports',
    )
    created_by = models.ForeignKey(
        EmployerIdentity,
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
    validated_at = models.DateTimeField(null=True)
    initial_sent_at = models.DateTimeField(null=True)
    synced_at = models.DateTimeField(null=True)
    sandbox_response = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'journeys_employerimport'


class EmployerEmailLink(models.Model):
    """Single-use local email verification, optionally carrying one explicitly submitted draft."""

    pending_import = models.ForeignKey(
        EmployerImport, null=True, blank=True, on_delete=models.PROTECT
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
        EmployerImport, on_delete=models.PROTECT, related_name='search_operations'
    )
    requested_by = models.ForeignKey(EmployerIdentity, on_delete=models.PROTECT)
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
    actor = models.ForeignKey(EmployerIdentity, on_delete=models.PROTECT)
    state = models.CharField(max_length=12)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_employersearchevent'
