from django.urls import path
from . import views
from . import employer_api
urlpatterns=[
path('access/', views.access, name='access'),
path('demo/<int:pk>/', views.demo_login, name='demo_login'),
path('confirm/<str:token>/', views.confirm, name='confirm'),
path('logout/', views.sign_out, name='logout'),
path('', views.dashboard, name='dashboard'),
path('offers/<int:pk>/', views.offer, name='offer'),
path('upload/', views.upload, name='upload'),
path('documents/<int:pk>/', views.document, name='document'),
path('profile/', views.candidate_edit, name='candidate_edit'),
path('matches/<int:pk>/', views.match_detail, name='match'),
path('conversations/<int:pk>/', views.conversation, name='conversation'),
path('conversations/<int:pk>/feed/', views.conversation_feed, name='conversation_feed'),
path('notifications/read/', views.read_notifications, name='read_notifications'),
path('manifest.webmanifest', views.manifest),
path('sw.js', views.service_worker),
path('imported-offers/<uuid:pk>/', views.imported_offer, name='imported_offer'),
path('local-api/imports/',employer_api.imports),
path('local-api/imports/source/',employer_api.read_source),
path('local-api/imports/<uuid:id>/',employer_api.imports),
path('previews/employer-landing/<path:path>',employer_api.preview),
path('forms/eures-beta/site.css',employer_api.historical_css)
]
