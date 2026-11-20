"""Retired URLs only. No application link should generate one of these addresses."""

# Retirement policy: keep an address for 30 days after its deployed retirement,
# then delete it in a maintenance commit, with its helper/tests/client allowlists.
# Record the retirement milestone and removal deadline beside each group.
# A rebase, refactor or helper change NEVER restarts the compatibility period.
# No wall-clock switch in production: removal is reviewed, tested and deployed.
# See docs/LEGACY_ROUTES.md for the inventory and pruning procedure.

from django.urls import path
from django.views.generic.base import RedirectView

from .redirects import (
    legacy_employer_dashboard,
    retired_employer_attachment,
    legacy_employer_page,
    legacy_import_api,
    legacy_workspace_route,
)

urlpatterns = [
    # Retired by #261, deployment pending: remove 30 days after that deployment.
    # Record the actual retirement/removal dates when #261 is first deployed.
    path('employer/offers/', legacy_employer_dashboard),
    path('employer/attach/', retired_employer_attachment),
    path('employer/drafts/<uuid:id>/attach/', retired_employer_attachment),
    # Already retired at the 2026-11-20 inventory: remove by 2026-12-20 latest.
    # The original deployment date is not reconstructed here; do not reset this bound.
    *[
        path(old_path, legacy_workspace_route, {'target': target})
        for old_path, target in (
            ('matching/candidate/', 'candidate_offer_inbox'),
            ('matching/candidate/<int:pk>/', 'candidate_offer_confirmation'),
            ('matching/candidate/<int:pk>/dialogue/', 'candidate_offer_dialogue'),
            ('accounts/dashboard/conversations/<int:pk>/', 'adviser_conversation'),
            ('matching/shared/start/<int:pk>/', 'shared_conversation_start'),
            ('matching/shared/<int:pk>/', 'shared_conversation'),
        )
    ],
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
        {'target': 'employer_profile'},
    ),
    path('employer/connected/', legacy_employer_dashboard),
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
