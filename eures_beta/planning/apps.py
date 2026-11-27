from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlanningConfig(AppConfig):
    name = "eures_beta.planning"
    verbose_name = _("Planning")
