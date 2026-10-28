from django.urls import path
from eures_beta.notifications import views

urlpatterns = [
    path('notifications/read/', views.read_notifications, name='read_notifications'),
]
