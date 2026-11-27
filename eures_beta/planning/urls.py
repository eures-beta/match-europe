from django.urls import path
from .views import planning

urlpatterns = [path("", planning, name="staff_planning")]
