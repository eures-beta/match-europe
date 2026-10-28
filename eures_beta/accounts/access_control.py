from functools import wraps

from django.conf import settings
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache


def identity(request):
    if request.user.is_authenticated:
        return request.user
    draft_id = request.session.get('draft_user')
    if draft_id:
        return User.objects.filter(
            pk=draft_id,
            profile__verified=False,
            profile__role__in=['candidate', 'employer'],
        ).first()
    return None


def require_identity(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not settings.DEMO_MODE:
            forbid()
        user = identity(request)
        if not user:
            return redirect('access')
        request.me_user = user
        return view(request, *args, **kwargs)

    return wrapped


def forbid():
    raise Http404()
