from django.urls import path
from . import views

urlpatterns = [
    path('access/', views.access, name='access'),
    path('demo/<int:pk>/', views.demo_login, name='demo_login'),
    path('confirm/<str:token>/', views.confirm, name='confirm'),
    path('logout/', views.sign_out, name='logout'),
]
