from django.urls import path
from . import views, team_views

urlpatterns = [
    path("employers/", team_views.employers, name="matching_team_employers"),
    path('teams/<int:team_id>/manual/', team_views.manual, name='matching_team_manual'),
    path('team-pairs/<int:pk>/', team_views.detail, name='matching_team_detail'),
    path('', views.index, name='matching'),
    path('<int:pk>/', views.detail, name='matching_detail'),
]
