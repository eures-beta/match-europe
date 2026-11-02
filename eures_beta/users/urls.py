from django.urls import path
from . import views

urlpatterns = [
    path('accounts/me/', views.account, name='account'),
    path('accounts/login/', views.login, name='magic_login'),
    path('accounts/confirm/', views.confirm, name='magic_confirm'),
    path('accounts/logout/', views.logout, name='magic_logout'),
]
