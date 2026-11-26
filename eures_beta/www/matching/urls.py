from django.urls import path
from eures_beta.www.adviser import matching as adviser_matching
from eures_beta.www.adviser import followup
from eures_beta.www.matching import (
    offer_reviews as confirmation_views,
    conversations,
    employer_consent,
    views,
)

urlpatterns = [
    path('follow-up/', followup.index, name='adviser_followup_list'),
    path('follow-up/<int:pk>/', followup.detail, name='adviser_followup'),
    path(
        'offer-reviews/<int:pk>/employer-consent/',
        employer_consent.prepare,
        name='prepare_employer_consent',
    ),
    path(
        'employer-consents/<int:pk>/',
        employer_consent.respond,
        name='respond_employer_consent',
    ),
    path('<int:pk>/review/', adviser_matching.detail, name='adviser_match'),
    path(
        'offer-reviews/<int:pk>/conversation/',
        conversations.start,
        name='shared_conversation_start',
    ),
    path('conversations/<int:pk>/', conversations.detail, name='shared_conversation'),
    path(
        'offer-reviews/<int:pk>/',
        adviser_matching.follow,
        name='adviser_conversation',
    ),
    path(
        '<int:pk>/confirmations/',
        confirmation_views.invite,
        name='request_candidate_confirmation',
    ),
    path('', views.index, name='matching'),
    path('<int:pk>/', views.detail, name='matching_detail'),
]
