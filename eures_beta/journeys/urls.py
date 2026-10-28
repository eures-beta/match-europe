from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload, name='upload'),
    path('matches/<int:pk>/', views.match_detail, name='match'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
