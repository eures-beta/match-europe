from django.urls import path
from . import views

urlpatterns = [
    path('documents/<int:pk>/', views.document, name='document'),
]
