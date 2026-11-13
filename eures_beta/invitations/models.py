import uuid
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from .defaults import invitation_expiry


class Invitation(models.Model):
    class RecipientKind(models.TextChoices):
        EMPLOYER = 'employer', 'Employeur'
        CANDIDATE = 'candidate', 'Candidat'
        ADVISER = 'adviser', 'Conseiller'

    recipient_kind = models.CharField(
        max_length=10, choices=RecipientKind.choices, default=RecipientKind.EMPLOYER
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nonce = models.UUIDField(default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    language = models.CharField(max_length=2, choices=settings.LANGUAGES, default='fr')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sent_invitations',
    )
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    recipient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invitation',
    )
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Preserve the existing table; moving an app must not recreate its data.
        db_table = 'users_invitation'
        constraints = [
            models.UniqueConstraint(Lower('email'), name='users_invitation_email_ci')
        ]

    @property
    def expired(self):
        return self.expires_at <= timezone.now()
