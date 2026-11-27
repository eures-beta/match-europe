from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IntroductionsConfig(AppConfig):
    name = 'eures_beta.introductions'
    verbose_name = _('Introductions')
