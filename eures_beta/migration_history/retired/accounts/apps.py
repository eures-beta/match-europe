from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'eures_beta.migration_history.retired.accounts'
    label = 'accounts'
    verbose_name = 'Retired accounts migration compatibility'
    default_auto_field = 'django.db.models.BigAutoField'
