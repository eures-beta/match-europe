from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    class Role(models.TextChoices):
        EMPLOYER = 'employer', _('Employer')
        CANDIDATE = 'candidate', _('Candidate')
        ADVISER = 'adviser', _('Adviser')
        ADMIN = 'admin', _('Administrator')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    verified = models.BooleanField(default=False)
    adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='supported_profiles',
    )
    name = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = 'journeys_profile'


class AccessToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'journeys_accesstoken'


class Event(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=40)
    object_id = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_event'
