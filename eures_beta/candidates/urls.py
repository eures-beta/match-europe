from django.urls import path
from eures_beta.candidates import landing, journey

urlpatterns = [
    path('candidate/prepare/', journey.journey, name='candidate_prepare'),
    path('candidate/', landing.landing, name='candidate_landing'),
]
