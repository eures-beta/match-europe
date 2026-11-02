"""Bounded, content-free request telemetry shared with the Gunicorn abort hook."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
import logging
import json
import os
import re
import sys
from threading import RLock
from time import perf_counter

logger = logging.getLogger('match_europe.performance')
current_request = ContextVar('performance_request', default=None)
active_requests = {}
registry_lock = RLock()
STAGES = frozenset(
    {
        'source_download',
        'source_parse',
        'document_extract',
        'geocode',
        'external_submission',
        'import_save',
    }
)


def label(value, fallback='unknown'):
    value = str(value)
    return value if re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', value) else fallback


def emit(event, fields, level=logging.INFO):
    # Only our own fixed-schema values enter this logger. Never format a request,
    # exception, SQL statement, external URL or arbitrary caller-provided dict.
    payload = {
        'event': event,
        'time': datetime.now(timezone.utc).isoformat(),
        'pid': os.getpid(),
        **fields,
    }
    try:
        logger.log(level, json.dumps(payload, separators=(',', ':'), ensure_ascii=True))
    except Exception:
        # Diagnostics must not turn a successful request into an outage.
        pass


@dataclass
class RequestStats:
    request_id: str
    method: str
    sampled: bool
    route: str = 'unresolved'
    started: float = field(default_factory=perf_counter)
    sql_in_flight: int = 0
    sql_count: int = 0
    sql_seconds: float = 0
    stages: dict = field(default_factory=dict)
    active_stages: list = field(default_factory=list)
    lock: RLock = field(default_factory=RLock)

    def fields(self):
        with self.lock:
            return {
                'request_id': self.request_id,
                'method': self.method,
                'route': self.route,
                'duration_ms': round((perf_counter() - self.started) * 1000, 3),
                'sql_count': self.sql_count,
                'sql_in_flight': self.sql_in_flight,
                'sql_ms': round(self.sql_seconds * 1000, 3),
                'sql_scope': 'request_thread',
                'stages': {name: dict(values) for name, values in self.stages.items()},
                'active_stages': list(self.active_stages),
                'release': label(
                    os.environ.get(
                        'COMMIT_ID', os.environ.get('CC_COMMIT_ID', 'unknown')
                    )
                ),
                'instance': label(os.environ.get('CC_INSTANCE_ID', 'unknown')),
            }

    def measure_sql(self, execute, sql, params, many, context):
        started = perf_counter()
        with self.lock:
            self.sql_in_flight += 1
        try:
            return execute(sql, params, many, context)
        finally:
            with self.lock:
                self.sql_in_flight -= 1
                self.sql_count += 1
                self.sql_seconds += perf_counter() - started


@contextmanager
def stage(name):
    if name not in STAGES:
        raise ValueError('Unknown fixed performance stage')
    stats = current_request.get()
    if stats is None:
        yield
        return
    started = perf_counter()
    failed = False
    with stats.lock:
        tracked = len(stats.active_stages) < 16
        if tracked:
            stats.active_stages.append(name)
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        duration = (perf_counter() - started) * 1000
        with stats.lock:
            if tracked:
                stats.active_stages.remove(name)
            item = stats.stages.setdefault(
                name, {'count': 0, 'duration_ms': 0, 'failed_count': 0}
            )
            item['count'] += 1
            item['duration_ms'] = round(item['duration_ms'] + duration, 3)
            item['failed_count'] += int(failed)


def timed_stage(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with stage(name):
                return function(*args, **kwargs)

        return wrapped

    return decorate


def worker_abort(worker):
    # Diagnostic before SIGKILL when Gunicorn can still invoke its abort hook.
    # Walk frames without source lines, arguments, exception messages or locals.
    with registry_lock:
        requests = list(active_requests.items())[:16]
    frames = sys._current_frames()
    for thread_id, stats in requests:
        frame = frames.get(thread_id)
        stack = []
        while frame is not None and len(stack) < 20:
            stack.append(
                {
                    'module': label(frame.f_globals.get('__name__', 'unknown')),
                    'function': label(frame.f_code.co_name),
                    'line': frame.f_lineno,
                }
            )
            frame = frame.f_back
        emit(
            'worker_timeout',
            {**stats.fields(), 'thread_id': thread_id, 'stack': stack},
            logging.ERROR,
        )
    if not requests:
        emit('worker_timeout', {'active_requests': 0}, logging.ERROR)
