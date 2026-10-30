from django.urls import path
from eures_beta.candidates import views, landing

urlpatterns = [
    path('candidate/', landing.landing, name='candidate_landing'),
    path('profile/', views.candidate_edit, name='candidate_edit'),
]
