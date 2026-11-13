from django.urls import path
from eures_beta.www.invitations import adviser, views

urlpatterns = [
    path('accounts/employers/invite/', views.invite, name='employer_invite'),
    path(
        'accounts/invitations/confirm/',
        views.confirm,
        name='invitation_confirm',
    ),
    path(
        'accounts/dashboard/invitations/',
        adviser.invitations_tab,
        name='adviser_invitations',
    ),
]
