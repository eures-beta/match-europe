"""Retired URLs only. No application link should generate one of these addresses."""

from django.urls import path
from django.views.generic.base import RedirectView

from .redirects import (
    legacy_employer_connected,
    legacy_employer_page,
    legacy_import_api,
    legacy_workspace_route,
)

urlpatterns = [
    path(
        'accounts/dashboard/matching/<int:pk>/',
        legacy_workspace_route,
        {'target': 'adviser_match'},
    ),
    path(
        'accounts/dashboard/invitations/',
        legacy_workspace_route,
        {'target': 'adviser_invitations'},
    ),
    path(
        'accounts/employers/invite/',
        legacy_workspace_route,
        {'target': 'employer_invite'},
    ),
    path(
        'api/employer/response-practice/',
        legacy_workspace_route,
        {'target': 'employer_response_practice'},
    ),
    path('employer/connected/', legacy_employer_connected),
    path('employer/pages/<path:path>', legacy_employer_page),
    path('previews/employer-landing/<path:path>', legacy_employer_page),
    # A cached browser script must preserve its POST body while switching API URLs.
    path('api/imports/', legacy_import_api),
    path('api/imports/source/', legacy_import_api, {'source': True}),
    path('api/imports/<uuid:id>/', legacy_import_api),
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
]
