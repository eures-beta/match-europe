"""One bounded JSON summary per sampled application request; no request content."""

from contextlib import ExitStack
import logging
from threading import get_ident
from time import thread_time
from uuid import uuid4

from django.conf import settings
from django.db import connections
from django.utils.deprecation import MiddlewareMixin

from .runtime import (
    RequestStats,
    active_requests,
    current_request,
    emit,
    label,
    registry_lock,
)


class RequestMetricsMiddleware(MiddlewareMixin):
    # Django adapts this synchronous middleware when used through ASGI. SQL
    # wrappers describe this request thread, not work started on other threads.
    sync_capable = True
    async_capable = False

    def __call__(self, request):
        if (
            not settings.REQUEST_METRICS_ENABLED
            or request.path_info == '/health/'
            or request.path_info.startswith('/static/')
        ):
            return self.get_response(request)
        request_id = uuid4().hex  # Never trust an inbound ID or log its value.
        sampled = int(request_id[:8], 16) / 2**32 < settings.REQUEST_METRICS_SAMPLE_RATE
        method = (
            request.method
            if request.method
            in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}
            else 'OTHER'
        )
        stats = RequestStats(request_id, method, sampled)
        cpu_started = thread_time()
        request._performance_stats = stats
        token = current_request.set(stats)
        thread_id = get_ident()
        with registry_lock:
            previous = active_requests.get(thread_id)
            active_requests[thread_id] = stats
        status = 500
        streaming = False
        try:
            with ExitStack() as wrappers:
                for connection in connections.all():
                    wrappers.enter_context(
                        connection.execute_wrapper(stats.measure_sql)
                    )
                response = self.get_response(request)
                status = response.status_code
                streaming = response.streaming
                response['X-Request-ID'] = request_id
                return response
        finally:
            with registry_lock:
                if previous is None:
                    active_requests.pop(thread_id, None)
                else:
                    active_requests[thread_id] = previous
            current_request.reset(token)
            stats.cpu_ms = round((thread_time() - cpu_started) * 1000, 3)
            fields = stats.fields()
            slow = fields['duration_ms'] >= settings.REQUEST_METRICS_SLOW_MS
            if sampled or slow or status >= 400:
                emit(
                    'request_completed',
                    {
                        **fields,
                        'status': status,
                        'duration_scope': (
                            'response_headers' if streaming else 'application'
                        ),
                    },
                    (
                        logging.ERROR
                        if status >= 500
                        else logging.WARNING if slow else logging.INFO
                    ),
                )

    def process_view(self, request, view_func, view_args, view_kwargs):
        stats = getattr(request, '_performance_stats', None)
        if stats is None:
            return
        match = request.resolver_match
        # Names and function names are developer-defined; never log URL kwargs.
        name = (
            match.view_name
            if match and match.url_name
            else getattr(view_func, '__module__', 'unknown')
            + '.'
            + getattr(view_func, '__name__', type(view_func).__name__)
        )
        stats.route = label(name)
        if stats.sampled and stats.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            emit('request_started', stats.fields())
