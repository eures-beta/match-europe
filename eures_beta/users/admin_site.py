"""Present adviser availability separately without inventing another Django app."""

from django.contrib.admin import AdminSite
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class PlanningAdminSite(AdminSite):
    def get_app_list(self, request, app_label=None):
        applications = super().get_app_list(request, app_label)
        result = []
        planning = []
        for application in applications:
            models = []
            for model in application['models']:
                if model['object_name'] == 'AdviserAvailability':
                    planning.append({**model, 'name': _('Adviser availability')})
                else:
                    models.append(model)
            if models:
                result.append({**application, 'models': models})
        if planning:
            result.append(
                {
                    'name': _('Planning'),
                    'app_label': 'adviser_planning',
                    'app_url': reverse(
                        'admin:users_adviseravailability_changelist',
                        current_app=self.name,
                    ),
                    'has_module_perms': True,
                    'models': planning,
                }
            )
        return sorted(result, key=lambda application: str(application['name']).lower())
