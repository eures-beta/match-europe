"""Keep technical model labels English while Django's interface stays localized."""

from django.contrib.admin import AdminSite
from django.utils.text import capfirst

from .admin_labels import EnglishModelOptions


class TechnicalModelNamesAdminSite(AdminSite):
    def get_app_list(self, request, app_label=None):
        applications = super().get_app_list(request, app_label)
        names = {
            (model._meta.app_label, model._meta.object_name): EnglishModelOptions(
                model._meta
            ).verbose_name_plural
            for model in self._registry
        }
        for application in applications:
            for model in application['models']:
                model['name'] = capfirst(
                    names[(application['app_label'], model['object_name'])]
                )
            application['models'].sort(key=lambda model: model['name'].casefold())
        return applications
