from django.urls import path
from eures_beta.candidates import landing

urlpatterns = [
    path('candidate/', landing.landing, name='candidate_landing'),
]
