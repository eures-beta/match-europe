from django.urls import path
from eures_beta.candidates import landing, journey, preview_push
from eures_beta.candidates import registration_views

urlpatterns = [
    path(
        'candidate/push-subscriptions/',
        preview_push.subscribe,
        name='candidate_push_subscriptions',
    ),
    path(
        'candidate/profile/compare/',
        registration_views.compare,
        name='candidate_profile_compare',
    ),
    path(
        'candidate/registration/requested/',
        registration_views.requested,
        name='candidate_registration_requested',
    ),
    path(
        'candidate/registration/confirm/',
        registration_views.confirm,
        name='candidate_registration_confirm',
    ),
    path('candidate/profile/', registration_views.profile, name='candidate_profile'),
    path(
        'candidate/profile/edit/',
        registration_views.edit,
        name='candidate_profile_edit',
    ),
    path('candidate/prepare/', journey.journey, name='candidate_prepare'),
    path('candidate/install-pwa/', landing.install_pwa, name='candidate_install_pwa'),
    path('candidate/', landing.landing, name='candidate_landing'),
]
