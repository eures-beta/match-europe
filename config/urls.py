from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from eures_beta.journeys import views
from eures_beta.journeys.redirects import legacy_employer_page
from .health import health

urlpatterns = [
    # Old tabs/bookmarks still contain these relative language links after deployment.
    path('previews/employer-landing/<path:path>', legacy_employer_page),
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
