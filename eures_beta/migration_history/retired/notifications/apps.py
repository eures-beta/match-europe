from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'eures_beta.migration_history.retired.notifications'
    label = 'notifications'
    verbose_name = 'Retired notifications migration compatibility'
    default_auto_field = 'django.db.models.BigAutoField'
