from django.urls import path
from . import views, employer_login, employer_workspace
from . import employer_api, push_test, employer_search

urlpatterns = [
    path(
        'employer/offers/<uuid:id>/search/',
        employer_search.launch,
        name='employer_search_launch',
    ),
    path(
        'employer/offers/<uuid:id>/search/check/',
        employer_search.check,
        name='employer_search_check',
    ),
    path(
        'employer/drafts/<uuid:id>/attach/',
        employer_workspace.resume_attachment,
        name='employer_resume_attachment',
    ),
    path('employer/offers/', employer_workspace.offers, name='employer_offers'),
    path(
        'employer/offers/<uuid:id>/', employer_workspace.detail, name='employer_offer'
    ),
    path(
        'employer/offers/<uuid:id>/edit/',
        employer_workspace.edit,
        name='employer_offer_edit',
    ),
    path(
        'employer/offers/<uuid:id>/duplicate/',
        employer_workspace.duplicate,
        name='employer_offer_duplicate',
    ),
    path('employer/attach/', employer_login.attach, name='employer_attach'),
    path('employer/email-sent/', employer_login.sent, name='employer_email_sent'),
    path('employer/access/', employer_login.access, name='employer_access'),
    path('employer/test-inbox/', employer_login.inbox, name='employer_test_inbox'),
    path(
        'employer/confirm/<str:token>/', employer_login.confirm, name='employer_confirm'
    ),
    path('employer/connected/', employer_login.connected, name='employer_connected'),
    path('employer/logout/', employer_login.sign_out, name='employer_logout'),
    path('local-api/push-test/<str:action>/', push_test.api),
    path('previews/employer-landing/push-test-sw.js', push_test.worker),
    path('previews/employer-landing/<path:path>', employer_api.preview),
    path('local-api/imports/', employer_api.imports),
    path('local-api/imports/source/', employer_api.read_source),
    path('local-api/imports/<uuid:id>/', employer_api.imports),
    path('imported-offers/<uuid:pk>/', views.imported_offer, name='imported_offer'),
    path('', views.dashboard, name='dashboard'),
    path('access/', views.access, name='access'),
    path('demo/<int:pk>/', views.demo_login, name='demo_login'),
    path('confirm/<str:token>/', views.confirm, name='confirm'),
    path('logout/', views.sign_out, name='logout'),
    path('upload/', views.upload, name='upload'),
    path('offers/<int:pk>/', views.offer, name='offer'),
    path('profile/', views.candidate_edit, name='candidate_edit'),
    path('matches/<int:pk>/', views.match_detail, name='match'),
    path('conversations/<int:pk>/', views.conversation, name='conversation'),
    path(
        'conversations/<int:pk>/feed/',
        views.conversation_feed,
        name='conversation_feed',
    ),
    path('documents/<int:pk>/', views.document, name='document'),
    path('notifications/read/', views.read_notifications, name='read_notifications'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
