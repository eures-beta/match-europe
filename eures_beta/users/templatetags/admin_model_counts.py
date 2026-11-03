"""Opt-in counts on the admin home, using each ModelAdmin's visible queryset."""

from django import template
from django.contrib import admin
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def model_counts_enabled(request):
    selected = request.GET.get('model_counts')
    if selected in ('0', '1'):
        enabled = selected == '1'
        if request.session.get('admin_model_counts', False) != enabled:
            request.session['admin_model_counts'] = enabled
        return enabled
    return request.session.get('admin_model_counts', False) is True


@register.simple_tag
def with_model_counts(app_list, request):
    if not model_counts_enabled(request):
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
