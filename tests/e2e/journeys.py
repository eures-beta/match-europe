"""Real HTTPS journeys: no Django test client, session injection or live services."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
import http.cookiejar
import json
from pathlib import Path
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .fixtures import SOURCE

ORIGIN = 'https://web:8443'
ARTIFACTS = Path('/artifacts')


class Inputs(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.values = {}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('type') == 'hidden' and attrs.get('name'):
            self.values[attrs['name']] = attrs.get('value', '')


class Browser:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
            urllib.request.HTTPSHandler(
                context=ssl.create_default_context(
                    cafile=str(ARTIFACTS / 'tls/cert.pem'),
                )
            ),
        )

    def request(
        self, path, fields=None, *, json_data=None, upload=None, status=200, csrf=True
    ):
        headers = {'Origin': ORIGIN, 'Referer': ORIGIN + '/'}
        data = None
        if fields is not None or json_data is not None:
            if csrf:
                token = next(
                    (x.value for x in self.cookies if x.name == 'csrftoken'), ''
                )
                headers['X-CSRFToken'] = token
            if json_data is not None:
                data = json.dumps(json_data).encode()
                headers['Content-Type'] = 'application/json'
            elif upload:
                boundary = uuid.uuid4().hex
                parts = []
                for key, value in fields.items():
                    parts.append(
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
                    )
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="fictional.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
                    + upload
                    + b'\r\n'
                )
                parts.append(f'--{boundary}--\r\n'.encode())
                data = b''.join(parts)
                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
            else:
                data = urllib.parse.urlencode(fields, doseq=True).encode()
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = urllib.request.Request(ORIGIN + path, data=data, headers=headers)
        try:
            response = self.client.open(request, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        body = response.read().decode()
        if response.status != status:
            raise AssertionError(
                f'{request.method} {urllib.parse.urlsplit(path).path}: expected {status}, received {response.status}'
            )
        return body

    def login(self, role):
        self.request('/accounts/login/?lang=en')
        self.request('/accounts/login/?lang=en', {'email': role + '@example.invalid'})
        self.confirm_mail(role + '@example.invalid', '/accounts/confirm/')

    def confirm_mail(self, recipient, path):
        links = []
        for file in (ARTIFACTS / 'mail').glob('*'):
            # Django's file backend can append several messages to one file.
            # Parse its message delimiter before checking each recipient.
            for raw in file.read_bytes().split(b'\n' + b'-' * 79 + b'\n'):
                if not raw.strip():
                    continue
                message = BytesParser(policy=policy.default).parsebytes(raw)
                if recipient not in str(message['To']):
                    continue
                content = message.get_body(preferencelist=('plain',)).get_content()
                links.extend(
                    re.findall(
                        r'https://web:8443' + re.escape(path) + r'\?[^\s<>]+', content
                    )
                )
        assert links, 'Expected captured confirmation email was not generated'
        self.request(links[-1].removeprefix(ORIGIN))
        self.request(path, {})


def pdf():
    """Small valid text PDF; pypdf must really extract its contents."""
    lines = SOURCE.splitlines()
    stream = 'BT /F1 10 Tf 40 780 Td 14 TL\n'
    for line in lines:
        stream += (
            '('
            + line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            + ') Tj T*\n'
        )
    stream = (stream + 'ET').encode()
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '
        + str(len(stream)).encode()
        + b' >>\nstream\n'
        + stream
        + b'\nendstream',
    ]
    output = b'%PDF-1.4\n'
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += b'xref\n0 6\n0000000000 65535 f \n'
    output += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    return (
        output
        + f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    )


def run(search_only=False):
    report = {'success': False, 'phase': 'occupation-cold', 'completed': []}
    started = time.monotonic()
    try:
        browser = Browser()
        browser.request('/accounts/login/?lang=en')  # CSRF only: never warm catalogs.
        query = {
            'q': 'industrial electrician',
            'lang': 'fr',
            'mode': 'search',
            'excluded': [],
            'independent': True,
            'context': 'maintain electrical equipment and repair industrial machines',
        }
        # Eight ordinary searches arriving at a cold eight-thread worker model
        # simultaneous users, without synthetic padding or a reduced catalog.
        clients = [browser, *[Browser() for _ in range(7)]]
        report['cold_search_concurrency'] = len(clients)
        for client in clients[1:]:
            client.request('/accounts/login/?lang=en')
        barrier = threading.Barrier(len(clients))

        def search(client):
            barrier.wait(timeout=10)
            return json.loads(client.request('/api/occupations/', json_data=query))

        before = time.monotonic()
        with ThreadPoolExecutor(max_workers=len(clients)) as pool:
            results = list(pool.map(search, clients))
        assert all(
            'results' in result and 'rome_results' in result for result in results
        )
        assert all(result == results[0] for result in results)
        report['cold_search_seconds'] = round(time.monotonic() - before, 3)
        report['completed'].append('occupation-cold')
        if not search_only:
            report['phase'] = 'public-pages-and-catalogs'
            for language, term in (
                ('fr', 'électricien'),
                ('en', 'electrician'),
                ('de', 'Elektriker'),
            ):
                for path in (
                    '/',
                    '/candidate/',
                    '/employer/?lang=' + language,
                ):
                    browser.request(path + '?lang=' + language)
                result = json.loads(
                    browser.request(
                        '/api/occupations/',
                        json_data={**query, 'q': term, 'lang': language},
                    )
                )
                assert result['results'], 'Full ESCO catalog must return real results'
            browser.request(
                '/api/occupations/', json_data=query, csrf=False, status=403
            )
            report['completed'].append(report['phase'])

            report['phase'] = 'employer-pdf-albert-save'
            employer = Browser()
            employer.login('employer')
            source = json.loads(
                employer.request(
                    '/api/job-offers/source/',
                    {'kind': 'pdf', 'agreement': 'true'},
                    upload=pdf(),
                )
            )
            assert (
                source['data']['extraction'] == 'albert_text'
            ), 'Fallback would hide an Albert integration failure'
            assert source['data']['companyName'] == 'Fictional Example SARL'
            saved = json.loads(
                employer.request(
                    '/api/job-offers/',
                    {
                        'kind': 'pdf',
                        'agreement': 'true',
                        'sourceToken': source['token'],
                        'contact': json.dumps(
                            {
                                'name': 'Fictional contact',
                                'email': 'employer@example.invalid',
                            }
                        ),
                    },
                    status=201,
                )
            )
            assert 'extractionSource' not in saved['data']
            offers = json.loads(employer.request('/api/job-offers/'))['drafts']
            assert saved['id'] in [offer['id'] for offer in offers]
            dashboard = employer.request('/accounts/dashboard/?lang=en')
            assert saved['data']['title'] in dashboard
            report['completed'].append(report['phase'])

            report['phase'] = 'adviser-invites-employer'
            adviser = Browser()
            adviser.login('adviser')
            adviser.request('/accounts/employers/invite/?lang=en')
            adviser.request(
                '/accounts/employers/invite/?lang=en',
                {'email': 'invited@example.invalid', 'language': 'en'},
            )
            invited = Browser()
            invited.confirm_mail(
                'invited@example.invalid', '/accounts/invitations/confirm/'
            )
            invited.request('/accounts/dashboard/?lang=en')
            assert json.loads(invited.request('/api/job-offers/'))['drafts'] == []
            invited.request('/api/job-offers/' + saved['id'] + '/', status=404)
            report['completed'].append(report['phase'])

            report['phase'] = 'candidate-questionnaire-confirmation'
            candidate = Browser()
            page = candidate.request('/candidate/prepare/?lang=fr')
            steps = [
                {'desired_occupations': 'Fictional job', 'desired_countries': ['FR']},
                {'mobility': 'discuss'},
                {
                    'availability': 'discuss',
                    'contract_types': ['discuss'],
                    'working_time': ['discuss'],
                    'schedule_preference': 'discuss',
                    'working_conditions': ['discuss'],
                    'salary_preference': 'discuss',
                },
                {
                    'display_name': 'Fictional candidate',
                    'contact_email': 'candidate@example.invalid',
                    'reviewed': 'on',
                },
            ]
            for step, fields in enumerate(steps, 1):
                token = Inputs(page).values['token']
                page = candidate.request(
                    f'/candidate/prepare/?step={step}&lang=fr',
                    {
                        **fields,
                        'token': token,
                        'action': 'finish' if step == 4 else 'continue',
                    },
                )
            candidate.confirm_mail(
                'candidate@example.invalid', '/candidate/registration/confirm/'
            )
            assert 'Fictional candidate' in candidate.request(
                '/candidate/profile/?lang=en'
            )
            report['completed'].append(report['phase'])
        report.update(success=True, phase='complete')
    except Exception as error:
        report['error'] = type(error).__name__
        # Only diagnostics without responses, cookies or magic-link query strings.
        if isinstance(error, AssertionError):
            report['detail'] = str(error)
    report['seconds'] = round(time.monotonic() - started, 3)
    (ARTIFACTS / 'journeys.json').write_text(json.dumps(report))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--health-only', action='store_true')
    parser.add_argument('--search-only', action='store_true')
    args = parser.parse_args()
    if args.health_only:
        Browser().request('/health/', status=204)
    else:
        raise SystemExit(run(args.search_only))
