"""Application routes, independent of technical Django endpoints."""

from django.urls import include, path
from django.views.generic.base import RedirectView
from eures_beta.www.public import views
from eures_beta.www.public.redirects import legacy_employer_page
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
    # Old tabs/bookmarks still contain these relative language links after deployment.
    path('previews/employer-landing/<path:path>', legacy_employer_page),
    path('privacy/', views.privacy, name='privacy'),
    path("", views.home, name="home"),
    path("statistics/", views.statistics, name="statistics"),
    path("project/", views.project, name="project"),
    path("journal/", views.journal, name="journal"),
    path("design-system/", views.design_system, name="design_system"),
    # Compatibility only: templates must use the canonical named routes.
    *[
        path(
            old_path,
            RedirectView.as_view(
                pattern_name=target,
                permanent=True,
                query_string=True,
                http_method_names=['get', 'head'],
            ),
            name=name,
        )
        for old_path, target, name in (
            ('forms/eures-beta/', 'home', 'legacy_home'),
            ('forms/eures-beta/candidate', 'candidate_landing', 'legacy_candidate'),
            ('forms/eures-beta/stat', 'statistics', 'legacy_statistics'),
            ('forms/eures-beta/le-projet', 'project', 'legacy_project'),
            ('forms/eures-beta/journal', 'journal', 'legacy_journal'),
        )
    ],
    path('manifest.webmanifest', views.manifest, name='pwa_manifest'),
    path('sw.js', views.service_worker, name='pwa_worker'),
]
