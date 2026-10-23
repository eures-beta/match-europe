from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from journeys import views
from .health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "",
        RedirectView.as_view(url="/previews/employer-landing/fr.html", permanent=False),
    ),
    path("", include("journeys.urls")),
    # Keep role navigation separate from the public employer entry point.
    path("dashboard/", views.dashboard, name="dashboard"),
]
