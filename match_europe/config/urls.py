from django.urls import include, path
from django.contrib.staticfiles.views import serve
urlpatterns=[path('static/<path:path>',serve,{'insecure':True}),path('',include('journeys.urls')),path('i18n/',include('django.conf.urls.i18n'))]
