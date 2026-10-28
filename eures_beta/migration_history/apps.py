"""Compatibility app: historical migrations only, no business models."""

from django.apps import AppConfig


class MigrationHistoryConfig(AppConfig):
    name = 'eures_beta.migration_history'
    label = 'journeys'
    verbose_name = 'Historical migration compatibility'
    default_auto_field = 'django.db.models.BigAutoField'
