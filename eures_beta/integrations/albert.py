"""Bounded Albert JSON client, independent of any business application."""

import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from django.conf import settings
from django.views.decorators.debug import sensitive_variables


class AlbertError(Exception):
    """A safe error code, never upstream content or credentials."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@sensitive_variables()
def complete_json(messages, *, max_tokens=3500):
    """Return decoded JSON; business prompts and schema validation stay with callers."""
    if not settings.ALBERT_API_KEY:
        raise AlbertError('albert_unavailable')
    payload = {
        'model': settings.ALBERT_MODEL,
        'messages': messages,
        'temperature': 0,
        'max_tokens': max_tokens,
        'stream': False,
        'response_format': {'type': 'json_object'},
    }
    request = Request(
        'https://albert.api.etalab.gouv.fr/v1/chat/completions',
        data=json.dumps(payload).encode(),
        headers={
            'Authorization': 'Bearer ' + settings.ALBERT_API_KEY,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    started = time.monotonic()
    try:
        with build_opener(NoRedirect()).open(request, timeout=35) as response:
            raw = response.read(100001)
        if len(raw) > 100000 or time.monotonic() - started > 40:
            raise ValueError()
        result = json.loads(raw)
        choice = result['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError()
        content = choice['message']['content']
        if isinstance(content, str):
            content = re.sub(
                r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', content.strip()
            )
        return json.loads(content)
    except HTTPError as exc:
        raise AlbertError('albert_http_' + str(exc.code)) from None
    except (OSError, URLError, ValueError, KeyError, IndexError, TypeError):
        raise AlbertError('albert_unavailable') from None
