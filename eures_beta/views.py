from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from eures_beta.accounts.access_control import identity


def interface(request):
    from eures_beta.demo import shared_notice

    user = identity(request)
    return {
        'me_user': user,
        'demo_mode': settings.DEMO_MODE,
        'shared_demo_notice': shared_notice(),
        'notifications': user.notifications.order_by('-created')[:8] if user else [],
    }


@never_cache
def home(request):
    if settings.DEMO_MODE:
        return redirect('/employer/pages/fr.html')
    return render(request, 'home.html')


def manifest(request):
    return JsonResponse(
        {
            'name': 'Match Europe',
            'short_name': 'Match Europe',
            'start_url': '/',
            'scope': '/',
            'display': 'standalone',
            'theme_color': '#003399',
            'background_color': '#f5f7fb',
            'icons': [
                {
                    'src': '/static/icon.svg',
                    'sizes': 'any',
                    'type': 'image/svg+xml',
                    'purpose': 'any',
                }
            ],
        },
        content_type='application/manifest+json',
    )


def service_worker(request):
    response = HttpResponse(
        (settings.APPS_DIR / 'static' / 'sw.js').read_text(),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
