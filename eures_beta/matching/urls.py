from django.urls import path
from . import confirmation_views, dialogue_views, views

urlpatterns = [
    path(
        "candidate/<int:pk>/dialogue/",
        dialogue_views.conversation,
        name="candidate_offer_dialogue",
    ),
    path('candidate/', confirmation_views.inbox, name='candidate_offer_inbox'),
    path(
        'candidate/<int:pk>/',
        confirmation_views.dialogue,
        name='candidate_offer_confirmation',
    ),
    path(
        '<int:pk>/confirmations/',
        confirmation_views.invite,
        name='request_candidate_confirmation',
    ),
    path('', views.index, name='matching'),
    path('<int:pk>/', views.detail, name='matching_detail'),
]
