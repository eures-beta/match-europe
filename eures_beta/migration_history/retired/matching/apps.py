from django.apps import AppConfig


class MatchingConfig(AppConfig):
    name = 'eures_beta.migration_history.retired.matching'
    label = 'matching'
    verbose_name = 'Retired matching migration compatibility'
    default_auto_field = 'django.db.models.BigAutoField'
