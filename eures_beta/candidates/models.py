from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from eures_beta.documents.models import Document


class Candidate(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate'
    )
    document = models.OneToOneField(
        Document, null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=150)
    experience = models.TextField(max_length=12000)
    jobs = models.CharField(max_length=500)
    skills = models.CharField(max_length=500, blank=True)
    languages = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=150)
    availability = models.CharField(max_length=150)
    cross_border = models.CharField(max_length=12)
    relocation = models.CharField(max_length=12)
    validated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'journeys_candidate'
