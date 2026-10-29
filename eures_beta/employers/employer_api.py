"""Loopback-only sandbox workflow. PostgreSQL drafts are session-owned; CSRF remains enabled."""

import json
import re
import math
import os
import time
import threading
import secrets
from html import escape
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction, connection
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.template.loader import get_template
from django.utils import timezone
from django.utils import translation
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from eures_beta.demo_access import require_demo_access as demo_api

from eures_beta.employers.models import EmployerImport
from eures_beta.employers.employer_ownership import accessible_imports, identity
from eures_beta.employers.forms import EmployerContactForm
from eures_beta.employers.offer_ingestion import (
    ImportFailure,
    empty_data,
    read_pdf,
    read_url,
    parse_pdf_text,
)

ROOT = Path(__file__).resolve().parents[2]
lock = threading.Lock()
last_geocode = 0.0


def local_only(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if (
            getattr(settings, 'SHARED_DEMO', False)
            or not settings.DEMO_MODE
            or request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1')
            or os.environ.get('ME_EMPLOYER_DEV_ACCESS') != '1'
        ):
            raise Http404()
        return view(request, *args, **kwargs)

    return wrapped


@demo_api
@ensure_csrf_cookie
def employer_page(request, path):
    if getattr(settings, 'SHARED_DEMO', False) and path == 'push-test.html':
        raise Http404()
    base = settings.APPS_DIR / 'templates' / 'employer'
    template_name = (
        'landing.html' if path in ('fr.html', 'en.html', 'de.html') else path
    )
    if path in ('privacy-en.html', 'privacy-fr.html', 'privacy-de.html'):
        template_name = 'privacy.html'
    if path in ('import-en.html', 'import-fr.html', 'import-de.html'):
        template_name = 'import.html'
    if path in ('import-v2-en.html', 'import-v2-fr.html', 'import-v2-de.html'):
        template_name = 'import-v2.html'
    candidate = (base / template_name).resolve()
    if (
        not candidate.is_relative_to(base.resolve())
        or not candidate.is_file()
        or candidate.suffix != '.html'
    ):
        raise Http404()
    if candidate.suffix == '.html':
        # Static build templates remain usable; served HTML activates the real same-origin API.
        person = identity(request)
        authenticated = bool(person and request.session.get('employer_verified_email'))
        body_tag = (
            '<body data-employer-api="true" data-employer-connected="'
            + ('true' if authenticated else 'false')
            + '">'
        )
        language = Path(path).stem.rsplit('-', 1)[-1]
        if path == 'push-test.html':
            language = request.GET.get('lang', request.LANGUAGE_CODE)
        language = language if language in ('fr', 'en', 'de') else request.LANGUAGE_CODE
        with translation.override(language):
            context = {}
            if path == 'push-test.html':
                from eures_beta.employers.push_strings import browser_strings

                context['push_strings'] = browser_strings()
            body = (
                get_template('employer/' + template_name)
                .render(context, request=request)
                .replace('<body>', body_tag)
            )
        from eures_beta.demo import shared_notice

        language = Path(path).stem.rsplit('-', 1)[-1]
        with translation.override(
            language if language in ('fr', 'en', 'de') else request.LANGUAGE_CODE
        ):
            notice = shared_notice()
        if notice:
            body = body.replace(
                body_tag,
                body_tag
                + '<aside role="note" style="padding:1rem;background:#fff3cd;color:#332701">'
                + escape(notice)
                + '</aside>',
                1,
            )
        if authenticated:
            lang = next(
                (code for code in ('fr', 'en', 'de') if path.endswith(code + '.html')),
                'fr',
            )
            with translation.override(lang):
                label = translation.gettext('My employer space')
            body = re.sub(
                r'(<a\s+class="nav-pill employer-account-link"\s+data-employer-account\s+href=")[^"]*(">)[^<]*(</a>)',
                lambda match: match[1]
                + '/employer/connected/?lang='
                + lang
                + match[2]
                + label
                + match[3],
                body,
            )
        return HttpResponse(body)
    return FileResponse(candidate.open('rb'))


def failure(code, status=400):
    return JsonResponse({'error': code}, status=status)


def body(request):
    if len(request.body) > 100000:
        raise ImportFailure('invalid_data')
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeError):
        raise ImportFailure('invalid_data') from None
    if not isinstance(value, dict):
        raise ImportFailure('invalid_data')
    return value


@demo_api
def read_source(request):
    if request.method != 'POST':
        return failure('method', 405)
    if request.POST.get('agreement') != 'true':
        return failure('agreement_required')
    try:
        url = request.POST.get('url', '').strip()
        kind = request.POST.get('kind', 'url')
        if kind == 'pdf':
            uploads = request.FILES.getlist('document')
            if not uploads:
                raise ImportFailure('missing')
            if (
                len(uploads) > 8
                or sum(upload.size for upload in uploads) > 10 * 1024 * 1024
            ):
                raise ImportFailure('large')
            if len(uploads) > 1 and any(
                not upload.name.lower().endswith(('.png', '.jpg', '.jpeg'))
                for upload in uploads
            ):
                raise ImportFailure('invalid')
            documents = (
                [read_pdf(upload, split_sections=False) for upload in uploads]
                if len(uploads) > 1
                else [read_pdf(uploads[0])]
            )
            data = documents[0]
            if len(documents) > 1:
                combined = '\n'.join(document['description'] for document in documents)
                if len(combined) > 16000:
                    raise ImportFailure('large')
                data = parse_pdf_text(combined)
                data['extraction'] = 'document_ocr'
                data['extractionWarnings'].append({'field': 'ocr', 'values': []})
            final = ''
        elif kind == 'url':
            data, final = read_url(url)
        elif kind == 'manual':
            text = request.POST.get('text', '').strip()
            if not text or len(text) > 16000:
                raise ImportFailure('invalid_data')
            data = empty_data()
            data['description'] = text
            data['extraction'] = 'manual'
            final = ''
        else:
            raise ImportFailure('invalid_data')
        token = secrets.token_urlsafe(24)
        request.session['pending_offer_source'] = {
            'kind': kind,
            'token': token,
            'url': url,
            'final': final,
            'data': data,
            'at': time.time(),
        }
        return JsonResponse(
            {
                'token': token,
                'data': data,
                'kind': kind,
                'source': final,
                'stage': 'review',
                'contact': {},
                'localOnly': os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1',
            }
        )
    except ImportFailure as exc:
        return failure(exc.code)


def clean_contact(value):
    if not isinstance(value, dict):
        raise ImportFailure('invalid_contact')
    form = EmployerContactForm(value)
    if not form.is_valid():
        raise ImportFailure('invalid_contact')
    return form.cleaned_data


@demo_api
def imports(request, id=None):
    if request.method == 'GET':
        if not request.session.session_key:
            return failure('not_found', 404) if id else JsonResponse({'drafts': []})
        qs = accessible_imports(request)
        if id:
            obj = qs.filter(pk=id).first()
            if not obj:
                return failure('not_found', 404)
            return JsonResponse(serialize(obj))
        return JsonResponse(
            {
                'drafts': [
                    {
                        'id': str(x.id),
                        'title': x.data.get('title', ''),
                        'updated': x.updated.isoformat(),
                        'synced': bool(x.synced_at),
                    }
                    for x in qs.order_by('-updated')[:30]
                ]
            }
        )
    if request.method != 'POST':
        return failure('method', 405)
    try:
        if not request.session.session_key:
            request.session.create()
        if id:
            obj = accessible_imports(request).filter(pk=id).first()
            if not obj:
                return failure('not_found', 404)
            payload = body(request)
            return update(request, obj, payload)
        person = (
            identity(request)
            if os.environ.get('ME_EMPLOYER_EMAIL_LOCAL') == '1'
            else None
        )
        if not request.session.get('employer_verified_email'):
            person = None
        if not request.session.session_key:
            request.session.create()
        if (
            not person
            and request.POST.get('connectedSubmission') == 'true'
            and request.POST.get('kind') in ('pdf', 'url')
            and not request.session.get('pending_offer_source')
        ):
            return failure('session_expired', 401)
        email = person.email if person else request.POST.get('email', '').strip()
        # An expired connected form can still preserve its explicit contact and draft.
        if not person and request.POST.get('connectedSubmission') == 'true':
            try:
                email = json.loads(request.POST.get('contact', '{}')).get('email', '')
            except (ValueError, AttributeError):
                raise ImportFailure('invalid_contact') from None
        try:
            validate_email(email)
        except ValidationError:
            raise ImportFailure('invalid_email') from None
        if len(email) > 254 or request.POST.get('agreement') != 'true':
            raise ImportFailure('agreement_required')
        if (
            EmployerImport.objects.filter(
                session_key=request.session.session_key
            ).count()
            >= 30
        ):
            raise ImportFailure('limit')
        try:
            contact = clean_contact(json.loads(request.POST.get('contact', '{}')))
        except (ValueError, TypeError):
            raise ImportFailure('invalid_contact') from None
        kind = request.POST.get('kind')
        source = ''
        if kind == 'url':
            source = request.POST.get('url', '').strip()
            pending = request.session.get('pending_offer_source', {})
            if (
                pending.get('kind', 'url') != 'url'
                or pending.get('token') != request.POST.get('sourceToken')
                or pending.get('url') != source
                or time.time() - pending.get('at', 0) > 900
            ):
                raise ImportFailure('unreadable_url')
            data = pending['data']
            source = pending['final']
        elif kind == 'pdf':
            pending = request.session.get('pending_offer_source', {})
            if (
                pending.get('kind') != 'pdf'
                or pending.get('token') != request.POST.get('sourceToken')
                or time.time() - pending.get('at', 0) > 900
            ):
                raise ImportFailure('unreadable')
            data = pending['data']
        elif kind == 'manual':
            text = request.POST.get('text', '').strip()
            if not text or len(text) > 16000:
                raise ImportFailure('invalid_data')
            data = empty_data()
            data['description'] = text
            data['extraction'] = 'manual'
        else:
            raise ImportFailure('invalid_data')
        if 'data' in request.POST:
            try:
                corrected = json.loads(request.POST['data'])
            except (ValueError, TypeError):
                raise ImportFailure('invalid_data') from None
            cleaned = clean_data(corrected)
            for key in ('extraction', 'extractionWarnings'):
                if key in data:
                    cleaned[key] = data[key]
            data = cleaned
        obj = EmployerImport.objects.create(
            created_by=person,
            session_key='' if person else request.session.session_key,
            email=email,
            contact=contact,
            preparation_agreed_at=timezone.now(),
            source_kind=kind,
            source_url=source,
            data=data,
        )
        if person:
            request.session['employer_claim_import'] = str(obj.pk)
        else:
            request.session['employer_pending_import'] = str(obj.pk)
        if kind in ('url', 'pdf'):
            request.session.pop('pending_offer_source', None)
        if os.environ.get('ME_EMPLOYER_EMAIL_LOCAL') == '1':
            # This ownership rehearsal must never trigger an external submission.
            return JsonResponse(
                {
                    **serialize(obj),
                    'login_url': (
                        '/employer/connected/' if person else '/employer/access/'
                    ),
                },
                status=201,
            )
        return initial_send(obj, created=True)
    except ImportFailure as exc:
        return failure(exc.code)


def serialize(obj):
    return {
        'id': str(obj.id),
        'contact': {'email': obj.email, **obj.contact},
        'data': obj.data,
        'revision': obj.revision,
        'source': obj.source_url,
        'kind': obj.source_kind,
        'synced': bool(obj.synced_at),
        'sandbox': obj.sandbox_response,
        'localOnly': os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1',
        'stage': (
            'review'
            if obj.initial_sent_at or os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1'
            else 'prepare'
        ),
    }


def initial_send(obj, created=False):
    if os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1':
        return JsonResponse(serialize(obj), status=201 if created else 200)
    data = obj.data
    if not all(data.get(k) for k in ('title', 'companyName', 'city', 'description')):
        return JsonResponse(serialize(obj), status=201 if created else 200)
    try:
        geo = data.get('geo')
        if not geo or geo.get('query') != data['city']:
            geo = geocode(data['city'])
        data['geo'] = geo
        post = {
            'id': str(obj.id),
            'title': data['title'],
            'companyName': data['companyName'],
            'description': data['description'],
            'desiredProfile': data.get('desiredProfile', ''),
            'workplaceLocation': {
                'city': data['city'][:50],
                'latitude': geo['latitude'],
                'longitude': geo['longitude'],
            },
            'createdAt': obj.created.isoformat(),
            'active': False,
        }
        if data.get('contractType'):
            post['contractType'] = data['contractType']
        aglae('POST', 'job-posting', {'jobPostings': [post]})
        returned = aglae('GET', f'job-posting/{obj.id}')
        if returned.get('id') != str(obj.id) or returned.get('active') is not False:
            raise ImportFailure('sandbox_error')
        for key in (
            'title',
            'companyName',
            'description',
            'desiredProfile',
            'contractType',
        ):
            if returned.get(key) is not None:
                data[key] = returned[key]
        # Keep full source address and geocoding provenance rather than the API's 50-character city limit.
        obj.data = data
        obj.sandbox_response = returned
        obj.initial_sent_at = timezone.now()
        obj.revision += 1
        obj.save()
        return JsonResponse(serialize(obj), status=201 if created else 200)
    except ImportFailure as exc:
        obj.data = data
        obj.save()
        return JsonResponse({'error': exc.code, **serialize(obj)}, status=502)


CONTRACTS = {
    'PERMANENT_CONTRACT',
    'FIXED_TERM_CONTRACT',
    'TEMPORARY_WORK',
    'INTERNSHIP',
    'APPRENTICESHIP',
    'FREELANCE',
    'TRAINING',
}


def clean_data(raw):
    if not isinstance(raw, dict):
        raise ImportFailure('invalid_data')
    out = empty_data()
    for key, limit in {
        'title': 125,
        'companyName': 100,
        'city': 150,
        'contractType': 32,
        'description': 16000,
        'desiredProfile': 4000,
    }.items():
        value = raw.get(key, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ImportFailure('invalid_data')
        out[key] = value.strip()
    if out['contractType'] and out['contractType'] not in CONTRACTS:
        raise ImportFailure('invalid_data')
    if 'occupation' in raw:
        from .occupation_selection import clean_selection

        try:
            out['occupation'] = clean_selection(raw['occupation'], out['title'])
        except ValueError:
            raise ImportFailure('invalid_data') from None
    clar = raw.get('clarifications', {})
    if not isinstance(clar, dict):
        raise ImportFailure('invalid_data')
    for key in out['clarifications']:
        value = clar.get(key, '')
        if not isinstance(value, str) or len(value) > 1000:
            raise ImportFailure('invalid_data')
        out['clarifications'][key] = value.strip()
    req = raw.get('requirements', {})
    if not isinstance(req, dict):
        raise ImportFailure('invalid_data')
    allowed = {
        'workConditions': {
            'early',
            'night',
            'weekend',
            'variable',
            'shift',
            'physical',
            'standing',
            'outdoor',
            'travel',
            'none',
            'unknown',
        },
        'permits': {'B', 'C', 'CE', 'D', 'DE', 'CACES', 'other'},
        'arrivalAids': {
            'housing',
            'admin',
            'transport',
            'onboarding',
            'other',
            'none',
            'unknown',
        },
    }
    for key, options in allowed.items():
        values = req.get(key, [])
        if (
            not isinstance(values, list)
            or len(values) > len(options)
            or any(not isinstance(v, str) or v not in options for v in values)
        ):
            raise ImportFailure('invalid_data')
        if (
            key != 'permits'
            and any(v in values for v in ('none', 'unknown'))
            and len(values) > 1
        ):
            raise ImportFailure('invalid_data')
        out['requirements'][key] = list(dict.fromkeys(values))
    value = req.get('permitRequired', '')
    if value not in ('', 'yes', 'no'):
        raise ImportFailure('invalid_data')
    out['requirements']['permitRequired'] = value
    for key in ('permitOther', 'aidOther'):
        value = req.get(key, '')
        if not isinstance(value, str) or len(value) > 500:
            raise ImportFailure('invalid_data')
        out['requirements'][key] = value.strip()
    if out['requirements']['permitRequired'] != 'yes':
        out['requirements']['permits'] = []
        out['requirements']['permitOther'] = ''
    if 'other' not in out['requirements']['permits']:
        out['requirements']['permitOther'] = ''
    if 'other' not in out['requirements']['arrivalAids']:
        out['requirements']['aidOther'] = ''
    for key in ('crossBorder', 'relocation'):
        value = raw.get(key, '')
        if value not in ('', 'yes', 'no', 'discuss'):
            raise ImportFailure('invalid_data')
        out[key] = value
    questions = raw.get('questions', [])
    if not isinstance(questions, list) or len(questions) > 20:
        raise ImportFailure('invalid_data')
    for q in questions:
        if (
            not isinstance(q, dict)
            or not isinstance(q.get('question'), str)
            or not 1 <= len(q['question'].strip()) <= 2000
            or type(q.get('mandatory')) is not bool
        ):
            raise ImportFailure('invalid_data')
        out['questions'].append(
            {
                'question': q['question'].strip(),
                'mandatory': q['mandatory'],
                'humanReviewRequired': True,
            }
        )
    return out


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def aglae(method, path, payload=None):
    # Shared previews never read a personal key or write to an external service.
    if getattr(settings, 'SHARED_DEMO', False):
        raise ImportFailure('api_key_missing')
    if os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1':
        raise ImportFailure('local_review_only')
    # Fixed sandbox origin; never accepted from the browser or a draft.
    keyfile = Path(
        os.environ.get(
            'AGLAE_SANDBOX_KEY_FILE',
            str(Path.home() / '.config/match-europe/aglae-sandbox.key'),
        )
    )
    try:
        key = keyfile.read_text().strip()
    except OSError:
        raise ImportFailure('api_key_missing') from None
    if not key:
        raise ImportFailure('api_key_missing')
    data = (
        json.dumps(payload, ensure_ascii=False).encode()
        if payload is not None
        else None
    )
    req = Request(
        'https://api-sandbox.saas.aglae.ai/v1-beta/' + path,
        method=method,
        data=data,
        headers={
            'X-Aglae-Api-Key': key,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        },
    )
    try:
        with build_opener(NoRedirect).open(req, timeout=30) as r:
            content = r.read(1024 * 1024)
            return json.loads(content) if content else {}
    except (OSError, HTTPError, URLError, ValueError):
        raise ImportFailure('sandbox_error') from None


def geocode(city):
    if os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1':
        raise ImportFailure('local_review_only')
    global last_geocode
    # Public workplace text only. No employer email or offer description is forwarded.
    query = urlencode({'q': city, 'format': 'jsonv2', 'limit': 1})
    with lock:
        pause = 1.1 - (time.monotonic() - last_geocode)
        if pause > 0:
            time.sleep(pause)
        try:
            text, _ = fetch_geocode(query)
            result = json.loads(text)
        except Exception:
            raise ImportFailure('geocode_error') from None
        finally:
            last_geocode = time.monotonic()
    if not result:
        raise ImportFailure('geocode_error')
    lat = float(result[0]['lat'])
    lon = float(result[0]['lon'])
    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or abs(lat) > 90
        or abs(lon) > 180
    ):
        raise ImportFailure('geocode_error')
    return {
        'latitude': lat,
        'longitude': lon,
        'label': str(result[0].get('display_name', ''))[:500],
        'query': city,
        'attribution': '© OpenStreetMap contributors / Nominatim',
    }


def fetch_geocode(query):
    request = Request(
        'https://nominatim.openstreetmap.org/search?' + query,
        headers={
            'User-Agent': 'MatchEurope-LocalSandbox/1.0 (local employer import test)',
            'Accept': 'application/json',
        },
    )
    with build_opener(NoRedirect).open(request, timeout=15) as r:
        return r.read(200000).decode(), None


def update(request, obj, payload):
    # PostgreSQL session advisory lock spans save + external write + readback.
    # It also serializes retries from another tab without storing API keys in the DB.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(hashtext(%s))', [str(obj.id)])
    try:
        return update_locked(request, obj, payload)
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(hashtext(%s))', [str(obj.id)])


def update_locked(request, obj, payload):
    action = payload.get('action')
    if action not in ('save', 'validate', 'locate', 'prepare', 'contact'):
        raise ImportFailure('invalid_data')
    if action == 'contact':
        contact = clean_contact(payload.get('contact'))
        with transaction.atomic():
            obj = (
                accessible_imports(request)
                .select_for_update()
                .filter(pk=obj.pk)
                .first()
            )
            if obj is None:
                return failure('not_found', 404)
            if obj.search_write_blocked:
                return failure('search_started', 409)
            if payload.get('revision') != obj.revision:
                return failure('conflict', 409)
            obj.contact = contact
            obj.revision += 1
            obj.save(update_fields=['contact', 'revision', 'updated'])
        return JsonResponse(serialize(obj))
    clean = clean_data(payload.get('data'))
    with transaction.atomic():
        obj = accessible_imports(request).select_for_update().filter(pk=obj.pk).first()
        if obj is None:
            return failure('not_found', 404)
        if obj.search_write_blocked:
            return failure('search_started', 409)
        if payload.get('revision') != obj.revision:
            return failure('conflict', 409)
        geo = obj.data.get('geo')
        if not geo or geo.get('query') != clean['city']:
            geo = None
        clean['extraction'] = obj.data.get('extraction', 'manual')
        clean['extractionWarnings'] = obj.data.get('extractionWarnings', [])
        if action == 'locate':
            geo = geocode(clean['city'])
        if geo:
            clean['geo'] = geo
        if action == 'validate':
            occupation = clean.get('occupation')
            if occupation is not None and not (
                occupation['uris'] or occupation['personal']
            ):
                raise ImportFailure('occupation_required')
            clean_contact(obj.contact)
            if not obj.initial_sent_at:
                raise ImportFailure('initial_required')
            if payload.get('confirmed') is not True or not all(
                clean[k]
                for k in ('title', 'companyName', 'city', 'description', 'contractType')
            ):
                raise ImportFailure('required')
            if not geo:
                geo = geocode(clean['city'])
                clean['geo'] = geo
            # Save corrections before the API call, including if the sandbox later fails.
        obj.data = clean
        obj.revision += 1
        obj.validated_at = None
        obj.synced_at = None
        obj.sandbox_response = {}
        obj.save()
    if action == 'prepare':
        return initial_send(obj)
    if action != 'validate':
        return JsonResponse(serialize(obj))
    # Record the validated version. Stable UUID makes a retry an update, not a duplicate creation.
    clarification = '\n'.join(
        f'{k}: {v}' for k, v in clean['clarifications'].items() if v
    )
    clarification += '\nCross-border recruitment: ' + (
        clean['crossBorder'] or 'unspecified'
    )
    clarification += '\nRelocation recruitment: ' + (
        clean['relocation'] or 'unspecified'
    )
    clarification += '\nJob conditions, permits and arrival support: ' + json.dumps(
        clean['requirements'], ensure_ascii=False
    )
    post = {
        'id': str(obj.id),
        'title': clean['title'],
        'companyName': clean['companyName'],
        'description': clean['description'],
        'desiredProfile': clean['desiredProfile'],
        'workplaceLocation': {
            'city': clean['city'][:50],
            'latitude': geo['latitude'],
            'longitude': geo['longitude'],
        },
        'contractType': clean['contractType'],
        'createdAt': obj.created.isoformat(),
        'active': False,
    }
    if clarification:
        post['additionalAgentDescription'] = (
            'Match Europe sandbox. Human review required.\n' + clarification
        )[:4000]
    try:
        aglae('POST', 'job-posting', {'jobPostings': [post]})
        # Automatic exclusion deliberately disabled in the external qualification engine.
        # Essential flags remain local for human review; no qualification is started.
        questions = [
            {
                'kind': 'standard',
                'code': f'ME_Q_{i+1}',
                'label': q['question'][:100],
                'question': q['question'],
                'rank': i,
                'isMandatory': False,
                'evaluationGuideline': 'Human review required. Do not reject automatically.',
            }
            for i, q in enumerate(clean['questions'])
        ]
        aglae(
            'PUT',
            f'job-posting/{obj.id}/specific-prerequisites',
            {'specificPrerequisites': questions},
        )
        returned = aglae('GET', f'job-posting/{obj.id}')
    except ImportFailure as exc:
        return JsonResponse({'error': exc.code, **serialize(obj)}, status=502)
    if returned.get('id') != str(obj.id) or returned.get('active') is not False:
        return failure('sandbox_error', 502)
    with transaction.atomic():
        current = EmployerImport.objects.select_for_update().get(pk=obj.pk)
        if current.revision != obj.revision:
            return failure('conflict', 409)
        current.validated_at = current.synced_at = timezone.now()
        current.sandbox_response = returned
        current.save()
    return JsonResponse(serialize(current))
