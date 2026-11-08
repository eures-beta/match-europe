from django.urls import path
from . import views, team_views, confirmation_views, dialogue_views

urlpatterns = [
    path(
        'candidate/<int:pk>/dialogue/',
        dialogue_views.conversation,
        name='candidate_offer_dialogue',
    ),
    path(
        "team-pairs/<int:pk>/confirmations/",
        confirmation_views.invite,
        name="request_candidate_confirmation",
    ),
    path("candidate/", confirmation_views.inbox, name="candidate_offer_inbox"),
    path(
        "candidate/<int:pk>/",
        confirmation_views.dialogue,
        name="candidate_offer_confirmation",
    ),
    path("employers/", team_views.employers, name="matching_team_employers"),
    path('teams/<int:team_id>/manual/', team_views.manual, name='matching_team_manual'),
    path('team-pairs/<int:pk>/', team_views.detail, name='matching_team_detail'),
    path('', views.index, name='matching_local'),
    path('<int:pk>/', views.detail, name='matching_detail'),
]
