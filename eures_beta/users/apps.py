from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'eures_beta.users'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from config import model_naming  # Register project model checks.
