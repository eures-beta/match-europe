from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class LoginRateLimit(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField(db_index=True)


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
    class Kind(models.TextChoices):
        ADVISER = 'adviser', _('Adviser')
        EMPLOYER = 'employer', _('Employer')

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
                condition=models.Q(kind__in=['adviser', 'employer']),
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
        return super().save(*args, **kwargs)
