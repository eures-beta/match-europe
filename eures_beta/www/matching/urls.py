from django.urls import path
from eures_beta.www.adviser import matching as adviser_matching
from eures_beta.www.matching import (
    confirmations as confirmation_views,
    conversations as shared_views,
    views,
)

urlpatterns = [
    path('<int:pk>/review/', adviser_matching.detail, name='adviser_match'),
    path(
        'offer-reviews/<int:pk>/conversation/',
        shared_views.start,
        name='shared_conversation_start',
    ),
    path('conversations/<int:pk>/', shared_views.detail, name='shared_conversation'),
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
