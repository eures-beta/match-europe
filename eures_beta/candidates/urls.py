from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.candidate_edit, name='candidate_edit'),
]
