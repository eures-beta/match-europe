from django.urls import path
from eures_beta.occupations.views import search_api
from eures_beta.employers import (
    employer_workspace,
    employer_api,
    response_practice_views,
)

urlpatterns = [
    path(
        'api/employer/response-practice/',
        response_practice_views.response_practice,
        name='employer_response_practice',
    ),
    path('api/occupations/', search_api, name='occupation_search'),
    path(
        'employer/drafts/<uuid:id>/attach/',
        employer_workspace.resume_attachment,
        name='employer_resume_attachment',
    ),
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
    path('employer/attach/', employer_workspace.attach, name='employer_attach'),
    path('employer/connected/', employer_workspace.offers, name='employer_connected'),
    path('employer/pages/<path:path>', employer_api.employer_page),
    path('api/imports/', employer_api.imports),
    path('api/imports/source/', employer_api.read_source),
    path('api/imports/<uuid:id>/', employer_api.imports),
]
