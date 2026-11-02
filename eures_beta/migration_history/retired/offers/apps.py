from django.apps import AppConfig


class OffersConfig(AppConfig):
    name = 'eures_beta.migration_history.retired.offers'
    label = 'offers'
    verbose_name = 'Retired offers migration compatibility'
    default_auto_field = 'django.db.models.BigAutoField'
