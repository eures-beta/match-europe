from django.urls import path
from eures_beta.documents import views

urlpatterns = [
    path('documents/<int:pk>/', views.document, name='document'),
]
