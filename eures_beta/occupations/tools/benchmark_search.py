"""Offline synthetic-title measurements; each case has a process-level deadline."""

import json
import subprocess
import sys


def main():
    failed = False
    program = '''
import json, resource, sys, time
from eures_beta.occupations.catalog import search_title, suggestions, rome_suggestions
title = 'Poste (' + 'h' * int(sys.argv[1])
start = time.perf_counter()
search_title(title)
normalization = time.perf_counter() - start
start = time.perf_counter()
suggestions(title, 'fr', 'Fictional job description for offline testing.')
rome_suggestions(title)
print(json.dumps({'normalization_ms': round(normalization * 1000, 3), 'search_ms': round((time.perf_counter() - start) * 1000, 3)}))
'''
    for count in (20, 24, 32):
        try:
            result = subprocess.run(
                [sys.executable, '-c', program, str(count)],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            print(
                json.dumps({'annotation_letters': count, **json.loads(result.stdout)})
            )
        except subprocess.TimeoutExpired:
            print(
                json.dumps({'annotation_letters': count, 'error': 'exceeded_5_seconds'})
            )
            failed = True
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
