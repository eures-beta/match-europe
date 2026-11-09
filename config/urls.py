from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from eures_beta import views
from eures_beta.redirects import legacy_employer_page
from .health import health
from eures_beta.skills.continuous_views import suggestions as skill_suggestions
from eures_beta.users import views as user_views

urlpatterns = [
    path(
        'api/occupation-skills/', skill_suggestions, name='occupation_skill_suggestions'
    ),
    path('', include('eures_beta.users.urls')),
    path("", include("eures_beta.employers.urls")),
    path("", include("eures_beta.candidates.urls")),
    # Old tabs/bookmarks still contain these relative language links after deployment.
    path('previews/employer-landing/<path:path>', legacy_employer_page),
    path("health/", health, name="health"),
    path('privacy/', views.privacy, name='privacy'),
    path('admin/login/', user_views.admin_login),
    path('admin/password_change/', user_views.password_disabled),
    path('admin/password_change/done/', user_views.password_disabled),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", views.home, name="home"),
    path("statistics/", views.statistics, name="statistics"),
    path("project/", views.project, name="project"),
    path("journal/", views.journal, name="journal"),
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
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
