from django.urls import path

from . import views

urlpatterns = [
    path('<int:pk>/', views.conversation, name='conversation'),
    path('<int:pk>/feed/', views.conversation_feed, name='conversation_feed'),
]
