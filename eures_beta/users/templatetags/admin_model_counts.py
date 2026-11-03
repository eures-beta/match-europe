"""Opt-in counts on the admin home, using each ModelAdmin's visible queryset."""

from django import template
from django.contrib import admin
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def with_model_counts(app_list, request):
    if request.GET.get('model_counts') != '1':
        return app_list
    counted_apps = []
    for app in app_list:
        models = []
        for entry in app['models']:
            entry = dict(entry)
            model_admin = admin.site.get_model_admin(entry['model'])
            if model_admin.has_view_permission(request):
                count = model_admin.get_queryset(request).count()
                entry['name'] = format_html('{} ({})', entry['name'], count)
            models.append(entry)
        counted_apps.append({**app, 'models': models})
    return counted_apps
