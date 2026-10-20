from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from .health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
]
