from django.urls import include, path
from django.contrib.staticfiles.views import serve

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('static/<path:path>', serve, {'insecure': True}),
    path('', include('journeys.urls')),
]
