from django.urls import path
from . import views

urlpatterns = [
    path('notifications/read/', views.read_notifications, name='read_notifications'),
]
