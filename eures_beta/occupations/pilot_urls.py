from django.urls import path

from . import pilot_views

urlpatterns = [
    path('', pilot_views.start, name='skills_pilot_start'),
    path('<str:role>/', pilot_views.journey, name='skills_pilot_journey'),
]
