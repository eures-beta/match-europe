from django.urls import path
from . import views, adviser_matching
from . import test_account_views

urlpatterns = [
    path(
        'accounts/test-accounts/', test_account_views.account_list, name='test_accounts'
    ),
    path(
        'accounts/test-accounts/sign-in/',
        test_account_views.sign_in,
        name='test_account_sign_in',
    ),
    path("accounts/dashboard/matching/<int:pk>/", adviser_matching.detail, name="adviser_match"),
    path("accounts/dashboard/conversations/<int:pk>/", adviser_matching.follow, name="adviser_conversation"),
    path('accounts/dashboard/', views.dashboard, name='dashboard'),
    path('accounts/me/', views.account, name='account'),
    path('accounts/login/', views.login, name='magic_login'),
    path('accounts/confirm/', views.confirm, name='magic_confirm'),
    path('accounts/logout/', views.logout, name='magic_logout'),
]
