from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eures_beta.migration_history.retired.conversations'
    label = 'conversations'
    verbose_name = 'Retired conversations migration compatibility'
