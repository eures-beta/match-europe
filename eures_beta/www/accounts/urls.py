from django.urls import path
from eures_beta.www.accounts import views
from eures_beta.www.accounts import test_accounts as test_account_views

urlpatterns = [
    path(
        'accounts/test-accounts/', test_account_views.account_list, name='test_accounts'
    ),
    path(
        'accounts/test-accounts/sign-in/',
        test_account_views.sign_in,
        name='test_account_sign_in',
    ),
    path('accounts/dashboard/', views.dashboard, name='dashboard'),
    path('accounts/me/', views.account, name='account'),
    path('accounts/login/', views.login, name='magic_login'),
    path('accounts/confirm/', views.confirm, name='magic_confirm'),
    path('accounts/logout/', views.logout, name='magic_logout'),
]
