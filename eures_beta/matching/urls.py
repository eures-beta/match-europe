from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='matching'),
    path('<int:pk>/', views.detail, name='matching_detail'),
]
