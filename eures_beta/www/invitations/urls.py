from django.urls import path
from eures_beta.www.invitations import adviser, views

urlpatterns = [
    path('adviser/invitations/new/', views.invite, name='employer_invite'),
    path(
        'accounts/invitations/confirm/',
        views.confirm,
        name='invitation_confirm',
    ),
    path(
        'adviser/invitations/',
        adviser.invitations_tab,
        name='adviser_invitations',
    ),
]
