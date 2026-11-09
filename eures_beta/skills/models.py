"""Shared reference suggestions, never candidate or employer declarations."""

from django.db import models


class OccupationSkillSuggestion(models.Model):
    occupation_uri = models.CharField(max_length=200)
    source_version = models.CharField(max_length=100)
    method = models.CharField(max_length=150)
    skill_uris = models.JSONField(default=list)
    status = models.CharField(max_length=10, default='pending')
    lease = models.UUIDField(null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'occupations_occupationskillsuggestion'
        constraints = [
            models.UniqueConstraint(
                fields=('occupation_uri', 'source_version', 'method'),
                name='unique_occupation_skill_suggestion',
            )
        ]
