from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from journeys import views
from .health import health
from .candidate import candidate_asset, candidate_entry, candidate_page

urlpatterns = [
    path("forms/eures-beta/candidate", candidate_entry, name="candidate_entry"),
    path("previews/employer-landing/candidate-<str:language>.html", candidate_page),
    path("previews/employer-landing/candidate.<str:asset>", candidate_asset),
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
