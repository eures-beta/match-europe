from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from eures_beta.documents.models import Document


class Offer(models.Model):
    class State(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING = 'pending', _('Awaiting email confirmation')
        READY = 'ready', _('Validated')
        SYNCED = 'synced', _('Sent to matching — demonstration')

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='offers'
    )
    adviser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='advised_offers',
    )
    document = models.OneToOneField(
        Document, null=True, blank=True, on_delete=models.SET_NULL
    )
    title = models.CharField(max_length=125)
    company = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    description = models.TextField(max_length=16000)
    contract = models.CharField(max_length=150, blank=True)
    salary = models.CharField(max_length=150, blank=True)
    hours = models.CharField(max_length=150, blank=True)
    languages = models.CharField(max_length=250, blank=True)
    skills = models.CharField(max_length=500, blank=True)
    cross_border = models.CharField(max_length=12, blank=True)
    relocation = models.CharField(max_length=12, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    validated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_offer'


class Question(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    expectation = models.CharField(max_length=500, blank=True)
    options = models.CharField(max_length=500, blank=True)
    mandatory = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'journeys_question'
        ordering = ['position', 'pk']

    def choices(self):
        return [x.strip() for x in self.options.split('|') if x.strip()]
