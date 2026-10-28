"""Shared access gate for prototype pages and endpoints; no business logic."""

import os
from functools import wraps

from django.conf import settings
from django.http import Http404
from django.views.decorators.cache import never_cache


def require_demo_access(view):
    """Require shared HTTPS or explicit loopback access, with caching disabled."""

    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        shared = getattr(settings, 'SHARED_DEMO', False)
        allowed = (
            request.is_secure()
            if shared
            else (
                request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
                and os.environ.get('ME_EMPLOYER_DEV_ACCESS') == '1'
            )
        )
        if not settings.DEMO_MODE or not allowed:
            raise Http404()
        return view(request, *args, **kwargs)

    return wrapped
