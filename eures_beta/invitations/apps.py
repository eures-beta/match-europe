from django.apps import AppConfig


class InvitationsConfig(AppConfig):
    name = 'eures_beta.invitations'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401
