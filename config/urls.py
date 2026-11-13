"""Technical endpoints and the common application router."""

from django.contrib import admin
from django.urls import include, path
from eures_beta.www.accounts import views as account_views
from .health import health

urlpatterns = [
    path('health/', health, name='health'),
    path('admin/login/', account_views.admin_login),
    path('admin/password_change/', account_views.password_disabled),
    path('admin/password_change/done/', account_views.password_disabled),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('eures_beta.www.urls')),
]
