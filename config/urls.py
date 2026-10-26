from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from eures_beta.journeys import views
from .health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "",
        RedirectView.as_view(url="/employer/pages/fr.html", permanent=False),
    ),
    path("", include("eures_beta.journeys.urls")),
    # Keep role navigation separate from the public employer entry point.
    path("dashboard/", views.dashboard, name="dashboard"),
]
