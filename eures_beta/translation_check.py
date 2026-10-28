"""Check committed gettext catalogs with GNU gettext, without a running app/DB."""

from pathlib import Path
import re
import subprocess
import sys


def incomplete_entries(path):
    problems = []
    for flag in ('--untranslated', '--only-fuzzy'):
        result = subprocess.run(
            ['msgattrib', flag, '--no-obsolete', str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        for block in result.stdout.split('\n\n'):
            if re.search(r'^msgid ', block, re.M) and not re.search(
                r'^msgid ""\nmsgstr ', block, re.M
            ):
                problems.append(block)
    return list(dict.fromkeys(problems))


def main():
    failed = False
    for language in ('fr', 'de'):
        path = Path(__file__).parent / 'locale' / language / 'LC_MESSAGES/django.po'
        entries = incomplete_entries(path)
        if entries:
            failed = True
            print(f'{language}: {len(entries)} untranslated/fuzzy messages')
            print('\n\n'.join(entries))
        else:
            print(f'{language}: all extracted messages translated')
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
