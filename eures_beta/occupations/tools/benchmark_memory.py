"""Measure a cold Django search in an isolated process, without database or network."""

import json
import subprocess
import sys

PROGRAM = '''
import json, os, resource, sys, time
os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY='memory-test-only', DJANGO_ALLOWED_HOSTS='testserver', EMAIL_DELIVERY_ENABLED='0', LOGIN_EMAIL_ENABLED='0')
import django
django.setup()
from django.test import Client
query = json.loads(sys.argv[1])
started = time.monotonic()
response = Client().post('/api/occupations/', query, content_type='application/json', secure=True)
assert response.status_code == 200, response.status_code
data = response.json()
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != 'darwin':
    peak *= 1024
print(json.dumps({'seconds': round(time.monotonic()-started, 3), 'peak_mib': round(peak/1048576, 2), 'esco': len(data['results']), 'rome': len(data['rome_results'])}))
'''


def measure():
    query = {
        'q': 'industrial electrician',
        'lang': 'fr',
        'mode': 'search',
        'excluded': [],
        'context': 'maintain electrical equipment and repair industrial machines',
        'independent': True,
    }
    result = subprocess.run(
        [sys.executable, '-c', PROGRAM, json.dumps(query)],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(result.stdout.splitlines()[-1])


if __name__ == '__main__':
    print(json.dumps(measure()))
