import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class LoginRateLimit(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField(db_index=True)


def invitation_expiry():
    return timezone.now() + timedelta(seconds=settings.EMPLOYER_INVITATION_MAX_AGE)


class EmployerInvitation(models.Model):
    class Audience(models.TextChoices):
        EMPLOYER = 'employer', 'Employeur'
        CANDIDATE = 'candidate', 'Candidat'
        ADVISER = 'adviser', 'Conseiller'

    audience = models.CharField(
        max_length=10, choices=Audience.choices, default=Audience.EMPLOYER
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nonce = models.UUIDField(default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    language = models.CharField(max_length=2, choices=settings.LANGUAGES, default='fr')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sent_employer_invitations',
    )
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    employer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='employer_invitation',
    )
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('email'), name='users_invitation_email_ci')
        ]

    @property
    def expired(self):
        return self.expires_at <= timezone.now()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, *, kind, **extra_fields):
        if not email or kind not in User.Kind.values:
            raise ValueError('An email and an explicit valid kind are required.')
        user = self.model(email=email.strip().lower(), kind=kind, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, *, kind, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('Superusers require staff and superuser privileges.')
        return self.create_user(email, password, kind=kind, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractUser):
    @property
    def has_candidate_invitation(self):
        return (
            self.kind == self.Kind.CANDIDATE
            and hasattr(self, 'employer_invitation')
            and self.employer_invitation.audience
            == EmployerInvitation.Audience.CANDIDATE
        )

    class Kind(models.TextChoices):
        ADVISER = 'adviser', _('Adviser')
        EMPLOYER = 'employer', _('Employer')
        CANDIDATE = 'candidate', _('Candidate')

    username = None
    email = models.EmailField(unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['kind']
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'), name='users_email_case_insensitive'
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=['adviser', 'employer', 'candidate']),
                name='users_valid_kind',
            ),
            models.CheckConstraint(
                condition=~models.Q(email=''), name='users_email_required'
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.kind not in self.Kind.values:
            raise ValidationError({'kind': _('An explicit valid kind is required.')})
        if self.pk and not self._state.adding:
            old = (
                type(self)
                .objects.using(kwargs.get('using') or self._state.db)
                .get(pk=self.pk)
            )
            if old.kind != self.kind:
                raise ValidationError({'kind': _('The user kind cannot be changed.')})
        adding = self._state.adding
        result = super().save(*args, **kwargs)
        if adding and self.kind == self.Kind.ADVISER and self.is_active:
            # Apply the versioned invitation role immediately to new advisers.
            from django.contrib.auth.models import Group
            from .permissions import EMPLOYER_INVITER_GROUP

            self.groups.add(
                *Group.objects.using(self._state.db).filter(name=EMPLOYER_INVITER_GROUP)
            )
        return result
