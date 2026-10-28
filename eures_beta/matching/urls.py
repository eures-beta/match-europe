from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('matches/<int:pk>/', views.match_detail, name='match'),
]
