from django.contrib import admin
from django.urls import include, path
from eures_beta import views
from eures_beta.documents import views as document_views
from eures_beta.matching.views import dashboard
from eures_beta.redirects import legacy_employer_page
from .health import health

urlpatterns = [
    path("", include("eures_beta.employers.urls")),
    path("", include("eures_beta.accounts.urls")),
    path("", include("eures_beta.offers.urls")),
    path("", include("eures_beta.candidates.urls")),
    path("", include("eures_beta.documents.urls")),
    path("", include("eures_beta.notifications.urls")),
    # Old tabs/bookmarks still contain these relative language links after deployment.
    path('previews/employer-landing/<path:path>', legacy_employer_page),
    path("conversations/", include("eures_beta.conversations.urls")),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", views.home, name="home"),
    path("", include("eures_beta.matching.urls")),
    path('upload/', document_views.upload, name='upload'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
    # Keep role navigation separate from the public employer entry point.
    path("dashboard/", dashboard, name="dashboard"),
]
