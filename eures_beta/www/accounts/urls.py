from django.urls import path
from eures_beta.www.adviser import action_queue
from eures_beta.www.adviser import offers as adviser_offers
from eures_beta.www.accounts import views
from eures_beta.www.accounts import test_accounts as test_account_views

urlpatterns = [
    path('adviser/offers/', adviser_offers.portfolio, name='adviser_offers'),
    path(
        'adviser/offers/import/',
        adviser_offers.import_offer,
        name='adviser_offer_import',
    ),
    path('adviser/offers/<uuid:id>/', adviser_offers.detail, name='adviser_offer'),
    path(
        'api/adviser/job-offers/',
        adviser_offers.deposits,
        name='adviser_offer_deposits',
    ),
    path(
        'api/adviser/job-offers/source/',
        adviser_offers.source,
        name='adviser_offer_source',
    ),
    path(
        'accounts/dashboard/search/<str:kind>/<uuid:pk>/',
        action_queue.search_detail,
        name='adviser_search',
    ),
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
