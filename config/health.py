from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


class HealthCheckMiddleware:
    """Answer only the health probe before host-dependent middleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info == "/health/":
            return health(request)
        return self.get_response(request)


@require_safe
@never_cache
def health(request):
    """Check database connectivity without exposing infrastructure details."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return HttpResponse(status=503)
    return HttpResponse(status=204)
