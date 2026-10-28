from django.urls import path
from eures_beta.offers import views

urlpatterns = [
    path('offers/<int:pk>/', views.offer, name='offer'),
]
