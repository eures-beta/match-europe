from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FollowupConfig(AppConfig):
    name = 'eures_beta.followup'
    verbose_name = _('Follow-up')
