from django.urls import path
from . import views
from . import invitation_views

urlpatterns = [
    path('accounts/employers/invite/', invitation_views.invite, name='employer_invite'),
    path(
        'accounts/invitations/confirm/',
        invitation_views.confirm,
        name='employer_invitation_confirm',
    ),
    path('accounts/dashboard/', views.dashboard, name='dashboard'),
    path('accounts/me/', views.account, name='account'),
    path('accounts/login/', views.login, name='magic_login'),
    path('accounts/confirm/', views.confirm, name='magic_confirm'),
    path('accounts/logout/', views.logout, name='magic_logout'),
]
