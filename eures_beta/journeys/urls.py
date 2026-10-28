from django.urls import path
from eures_beta.journeys import views

urlpatterns = [
    path('upload/', views.upload, name='upload'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
