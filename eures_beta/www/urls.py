"""Application routes, independent of technical Django endpoints."""

from django.urls import include, path
from eures_beta.www.public import views
from eures_beta.www.skills.views import suggestions as skill_suggestions

urlpatterns = [
    path('matching/', include('eures_beta.www.matching.urls')),
    path(
        'api/occupation-skills/', skill_suggestions, name='occupation_skill_suggestions'
    ),
    path('', include('eures_beta.www.accounts.urls')),
    path('', include('eures_beta.www.invitations.urls')),
    path("", include("eures_beta.www.employer.urls")),
    path("", include("eures_beta.www.candidate.urls")),
    path('privacy/', views.privacy, name='privacy'),
    path("", views.home, name="home"),
    path("statistics/", views.statistics, name="statistics"),
    path("project/", views.project, name="project"),
    path("journal/", views.journal, name="journal"),
    path("design-system/", views.design_system, name="design_system"),
    path(
        "design-system/exemple/",
        views.design_system_example,
        name="design_system_example",
    ),
    path(
        "design-system/exemple/<slug:screen>/",
        views.design_system_example,
        name="design_system_example_screen",
    ),
    path('', include('eures_beta.www.public.legacy_urls')),
    path('manifest.webmanifest', views.manifest, name='pwa_manifest'),
    path('sw.js', views.service_worker, name='pwa_worker'),
]
