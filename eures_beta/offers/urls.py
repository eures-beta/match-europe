from django.urls import path
from . import views

urlpatterns = [
    path('offers/<int:pk>/', views.offer, name='offer'),
]
