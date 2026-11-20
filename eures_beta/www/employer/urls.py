from django.urls import path
from eures_beta.www.occupations.views import search_api
from eures_beta.www.employer import (
    pages,
    workspace as employer_workspace,
    imports as employer_api,
    profile as profile_views,
)

urlpatterns = [
    path('employer/', pages.landing, name='employer_landing'),
    path('employer/import/', pages.import_offer, name='employer_import'),
    path('employer/privacy/', pages.privacy, name='employer_privacy'),
    path(
        'api/employer/profile/',
        profile_views.profile,
        name='employer_profile',
    ),
    path('api/occupations/', search_api, name='occupation_search'),
    path('employer/offers/', employer_workspace.offers, name='employer_offers'),
    path(
        'employer/offers/<uuid:id>/', employer_workspace.detail, name='employer_offer'
    ),
    path(
        'employer/offers/<uuid:id>/edit/',
        employer_workspace.edit,
        name='employer_offer_edit',
    ),
    path(
        'employer/offers/<uuid:id>/duplicate/',
        employer_workspace.duplicate,
        name='employer_offer_duplicate',
    ),
    path('api/job-offers/', employer_api.imports, name='job_offer_list'),
    path('api/job-offers/source/', employer_api.read_source, name='job_offer_source'),
    path('api/job-offers/<uuid:id>/', employer_api.imports, name='job_offer_data'),
]
