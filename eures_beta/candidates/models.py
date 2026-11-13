"""Durable candidate answers, separate from the anonymous session rehearsal."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


def registration_expiry():
    return timezone.now() + timedelta(seconds=settings.CANDIDATE_REGISTRATION_MAX_AGE)


class CandidateProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidate_profile',
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    display_name = models.CharField(max_length=150)
    language = models.CharField(max_length=2, choices=settings.LANGUAGES, default='fr')
    email_verified_at = models.DateTimeField(null=True, blank=True)
    notice_read_at = models.DateTimeField(null=True, blank=True)
    notice_version = models.CharField(max_length=32, blank=True)
    project_mode = models.CharField(
        max_length=16,
        default='occupation',
        choices=[
            ('occupation', _('I have one or more occupations in mind')),
            ('open', _('I am open to different occupations')),
        ],
    )
    acquired_skills = models.JSONField(default=list, blank=True)
    learning_activities = models.JSONField(default=list, blank=True)
    professional_behaviours = models.JSONField(default=list, blank=True)
    skill_catalogue_version = models.CharField(max_length=64, blank=True)
    occupation_skills = models.JSONField(default=dict, blank=True)
    desired_occupations = models.CharField(max_length=500, blank=True)
    occupation_references = models.JSONField(default=list, blank=True)
    desired_countries = models.JSONField(default=list)
    desired_locations = models.CharField(max_length=500, blank=True)
    mobility = models.CharField(max_length=16)
    commute_time = models.CharField(max_length=16, blank=True)
    transport_modes = models.JSONField(default=list, blank=True)
    transport_details = models.CharField(max_length=500, blank=True)
    language_skills = models.JSONField(default=dict, blank=True)
    licences_held = models.JSONField(default=list, blank=True)
    licence_details = models.CharField(max_length=500, blank=True)
    availability = models.CharField(max_length=16)
    available_from = models.DateField(null=True, blank=True)
    contract_types = models.JSONField(default=list)
    contract_details = models.CharField(max_length=500, blank=True)
    working_time = models.JSONField(default=list)
    schedule_preference = models.CharField(max_length=16)
    schedule_strict = models.BooleanField(default=False)
    schedule_monday = models.JSONField(default=list, blank=True)
    schedule_tuesday = models.JSONField(default=list, blank=True)
    schedule_wednesday = models.JSONField(default=list, blank=True)
    schedule_thursday = models.JSONField(default=list, blank=True)
    schedule_friday = models.JSONField(default=list, blank=True)
    schedule_saturday = models.JSONField(default=list, blank=True)
    schedule_sunday = models.JSONField(default=list, blank=True)
    working_conditions = models.JSONField(default=list)
    condition_details = models.TextField(max_length=4000, blank=True)
    salary_preference = models.CharField(max_length=16)
    salary_amount = models.DecimalField(
        max_digits=11, decimal_places=2, null=True, blank=True
    )
    salary_currency = models.CharField(max_length=3, blank=True)
    salary_period = models.CharField(max_length=8, blank=True)
    salary_basis = models.CharField(max_length=8, blank=True)

    class Meta:
        verbose_name = _('Candidate profile')
        verbose_name_plural = _('Candidate profiles')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(language__in=['fr', 'en', 'de']),
                name='candidate_profile_language',
            ),
            models.CheckConstraint(
                condition=models.Q(salary_amount__isnull=True)
                | models.Q(salary_amount__gte=0),
                name='candidate_profile_nonnegative_salary',
            ),
        ]

    def __str__(self):
        # Neither contact details nor questionnaire answers in implicit logs.
        return str(self.pk)

    def clean(self):
        super().clean()
        if (
            self.user_id
            and not type(self)
            .user.field.remote_field.model.objects.filter(
                pk=self.user_id, kind='candidate'
            )
            .exists()
        ):
            raise ValidationError({'user': _('A candidate account is required.')})

        # Use the current server-side questionnaire rules, including conditional
        # answers, catalogue references and schedule consistency. UI bookkeeping
        # and identity/email verification are deliberately outside this model.
        from eures_beta.candidates.forms import (
            ProjectForm,
            MobilityForm,
            ConditionsForm,
        )

        errors = {}
        for form_class in (ProjectForm, MobilityForm, ConditionsForm):
            kwargs = {'language': self.language} if form_class is ProjectForm else {}
            names = set(form_class(**kwargs).fields) & {
                field.name for field in self._meta.fields
            }
            data = {name: getattr(self, name) for name in names}
            form = form_class(data, **kwargs)
            if not form.is_valid():
                errors.update(form.errors.as_data())
                continue
            for name in names:
                value = form.cleaned_data[name]
                if name == 'salary_amount' and value == '':
                    value = None
                setattr(self, name, value)
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        # Validation normalises conditional fields as well, so persist the full
        # coherent record rather than a caller's partial selection of columns.
        if kwargs.get('update_fields') is not None:
            raise ValueError('Candidate profiles require a complete save.')
        return super().save(*args, **kwargs)


class PreviewPushSubscription(models.Model):
    candidate = models.OneToOneField(CandidateProfile, on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=2048, unique=True)
    keys = models.JSONField()
