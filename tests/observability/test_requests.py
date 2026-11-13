import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.http import HttpResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from eures_beta.observability.middleware import RequestMetricsMiddleware
from eures_beta.observability.runtime import (
    RequestStats,
    active_requests,
    current_request,
    stage,
    timed_stage,
    worker_abort,
)

LOG = 'match_europe.performance'


@override_settings(
    REQUEST_METRICS_ENABLED=True,
    REQUEST_METRICS_SAMPLE_RATE=1,
    REQUEST_METRICS_SLOW_MS=1000,
)
class RequestTests(SimpleTestCase):
    def request(self, view, path='/', method='get', route='safe_route'):
        request = getattr(RequestFactory(), method)(
            path, data={'email': 'secret@example.invalid', 'token': 'private-token'}
        )
        request.resolver_match = SimpleNamespace(view_name=route, url_name=route)

        def get_response(request):
            middleware.process_view(request, view, (), {'token': 'private-token'})
            return view(request)

        middleware = RequestMetricsMiddleware(get_response)
        return middleware(request)

    def events(self, captured):
        return [json.loads(record.getMessage()) for record in captured.records]

    def test_fixed_schema_excludes_all_request_content_and_uses_own_id(self):
        def view(request):
            request.META['HTTP_AUTHORIZATION'] = 'Bearer secret-api-key'
            request.COOKIES['sessionid'] = 'private-session'
            request.META['HTTP_X_REQUEST_ID'] = 'untrusted-request-id'
            with stage('source_download'):
                pass
            return HttpResponse('private response body')

        with self.assertLogs(LOG, level='INFO') as logs:
            response = self.request(
                view, '/confirm/private-token/?sesame=private-token', 'post'
            )
        events = self.events(logs)
        self.assertEqual(
            [e['event'] for e in events], ['request_started', 'request_completed']
        )
        result = events[-1]
        self.assertEqual(result['route'], 'safe_route')
        self.assertEqual(result['request_id'], response['X-Request-ID'])
        self.assertEqual(result['stages']['source_download']['count'], 1)
        for value in (
            'secret@example.invalid',
            'private-token',
            'private-session',
            'private response body',
            'secret-api-key',
            'untrusted-request-id',
            '/confirm/',
        ):
            self.assertNotIn(value, json.dumps(events))
        self.assertEqual(active_requests, {})
        self.assertIsNone(current_request.get())

    @override_settings(REQUEST_METRICS_SAMPLE_RATE=0)
    def test_sampling_keeps_slow_requests_and_errors(self):
        with self.assertNoLogs(LOG):
            self.request(lambda r: HttpResponse())
        with self.assertLogs(LOG) as logs:
            self.request(lambda r: HttpResponse(status=500))
        self.assertEqual(self.events(logs)[-1]['status'], 500)
        with override_settings(REQUEST_METRICS_SLOW_MS=0), self.assertLogs(LOG):
            self.request(lambda r: HttpResponse())

    def test_health_and_static_are_not_instrumented(self):
        for path in ('/health/', '/static/site.css'):
            with self.subTest(path=path), self.assertNoLogs(LOG):
                self.request(lambda r: HttpResponse(), path)

    @override_settings(REQUEST_METRICS_ENABLED=False)
    def test_can_disable_without_affecting_response(self):
        with self.assertNoLogs(LOG):
            response = self.request(lambda r: HttpResponse())
        self.assertNotIn('X-Request-ID', response)

    def test_failed_stage_and_request_cleanup_do_not_log_exception_text(self):
        def view(request):
            with stage('document_extract'):
                raise ValueError('private-document-content')

        with self.assertLogs(LOG) as logs, self.assertRaises(ValueError):
            self.request(view)
        result = self.events(logs)[-1]
        self.assertEqual(result['status'], 500)
        self.assertEqual(result['stages']['document_extract']['failed_count'], 1)
        self.assertNotIn('private-document-content', json.dumps(result))
        self.assertIsNone(current_request.get())
        self.assertEqual(active_requests, {})

    def test_streaming_duration_explicitly_measures_headers_not_transfer(self):
        with self.assertLogs(LOG) as logs:
            response = self.request(lambda r: StreamingHttpResponse(iter([b'content'])))
        self.assertEqual(self.events(logs)[-1]['duration_scope'], 'response_headers')
        response.close()

    def test_concurrent_requests_keep_separate_contexts(self):
        barrier = Barrier(2)

        def work(number):
            def view(request):
                with stage('source_parse'):
                    barrier.wait(timeout=5)
                    self.assertEqual(current_request.get().route, 'route' + str(number))
                return HttpResponse()

            return self.request(view, route='route' + str(number))['X-Request-ID']

        with self.assertLogs(LOG), ThreadPoolExecutor(max_workers=2) as pool:
            identifiers = list(pool.map(work, (1, 2)))
        self.assertNotEqual(*identifiers)
        self.assertEqual(active_requests, {})

    def test_unknown_paths_are_not_used_as_route_labels(self):
        request = RequestFactory().get('/private-unmatched-secret')
        with self.assertLogs(LOG) as logs:
            RequestMetricsMiddleware(lambda r: HttpResponse(status=404))(request)
        self.assertEqual(self.events(logs)[-1]['route'], 'unresolved')
        self.assertNotIn('private-unmatched-secret', str(logs.output))

    def test_timeout_snapshot_is_bounded_and_does_not_include_locals(self):
        def view(request):
            private_value = 'secret-local-value'
            with stage('document_extract'):
                worker_abort(None)
            return HttpResponse(private_value)

        with self.assertLogs(LOG) as logs:
            self.request(view)
        event = next(e for e in self.events(logs) if e['event'] == 'worker_timeout')
        self.assertEqual(event['active_stages'], ['document_extract'])
        self.assertLessEqual(len(event['stack']), 20)
        self.assertTrue(
            all(
                set(frame) == {'module', 'function', 'line'} for frame in event['stack']
            )
        )
        self.assertNotIn('secret-local-value', str(logs.output))

    def test_actual_parser_is_instrumented_without_logging_input(self):
        from eures_beta.employers.offer_ingestion import parse_page

        def view(request):
            parse_page(
                '<html><body>' + ('private-offer-description ' * 5) + '</body></html>'
            )
            return HttpResponse()

        with self.assertLogs(LOG) as logs:
            self.request(view)
        result = self.events(logs)[-1]
        self.assertEqual(result['stages']['source_parse']['count'], 1)
        self.assertNotIn('private-offer-description', str(logs.output))

    def test_gunicorn_configuration_and_hook_do_not_expose_urls(self):
        from pathlib import Path
        import runpy
        from django.conf import settings

        config = runpy.run_path(str(settings.BASE_DIR / 'gunicorn.conf.py'))
        self.assertIs(config['worker_abort'], worker_abort)
        for marker in ('%(U)', '%(q)', '%(r)', '%(h)'):
            self.assertNotIn(marker, config['access_log_format'])
            self.assertNotIn(
                marker, (settings.BASE_DIR / 'clevercloud/run.sh').read_text()
            )

    def test_stage_names_are_fixed_and_no_context_is_a_noop(self):
        with self.assertRaises(ValueError):
            with stage('private-url'):
                pass

        @timed_stage('source_parse')
        def normal(value):
            return value

        self.assertEqual(normal('input'), 'input')

    def test_logging_failure_cannot_break_request(self):
        with patch('eures_beta.observability.runtime.logger.log', side_effect=OSError):
            self.assertEqual(self.request(lambda r: HttpResponse()).status_code, 200)


class SQLTests(TestCase):
    def test_sql_counts_and_timings_without_debug_or_sql_contents(self):
        def view(request):
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s", ['private-sql-value'])
                self.assertEqual(cursor.fetchone()[0], 'private-sql-value')
            return HttpResponse()

        with self.assertLogs(LOG) as logs:
            response = RequestMetricsMiddleware(view)(RequestFactory().get('/'))
        event = json.loads(logs.records[-1].getMessage())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(event['sql_count'], 1)
        self.assertGreaterEqual(event['sql_ms'], 0)
        self.assertEqual(event['sql_in_flight'], 0)
        self.assertNotIn('private-sql-value', str(logs.output))
        self.assertNotIn('SELECT', str(logs.output))

    def test_real_django_requests_and_async_adaptation_have_request_ids(self):
        from asgiref.sync import async_to_sync
        from django.test import AsyncClient

        for response in (self.client.get('/'), async_to_sync(AsyncClient().get)('/')):
            self.assertEqual(response.status_code, 200)
            self.assertRegex(response['X-Request-ID'], r'^[a-f0-9]{32}$')
