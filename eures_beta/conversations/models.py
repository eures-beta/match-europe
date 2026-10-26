from django.conf import settings
from django.db import models


class Conversation(models.Model):
    match = models.OneToOneField(
        'journeys.Match', on_delete=models.PROTECT, related_name='conversation'
    )
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_conversation'


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created', 'pk']
        db_table = 'journeys_message'
