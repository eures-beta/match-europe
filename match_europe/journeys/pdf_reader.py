"""Bounded PDF text extraction in a separate process. Never execute PDF actions."""

import io
import json
import resource
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

from pypdf import PdfReader


def ocr(data, suffix, page=0):
    executable = shutil.which('tesseract')
    renderer = shutil.which('pdftoppm')
    if not executable or (suffix == '.pdf' and not renderer):
        raise ValueError('ocr_unavailable')
    with tempfile.TemporaryDirectory(prefix='me-ocr-') as directory:
        source = Path(directory) / ('document' + suffix)
        source.write_bytes(data)
        if suffix == '.pdf':
            target = Path(directory) / 'page'
            subprocess.run(
                [
                    renderer,
                    '-f',
                    str(page + 1),
                    '-l',
                    str(page + 1),
                    '-singlefile',
                    '-scale-to',
                    '3200',
                    '-png',
                    str(source),
                    str(target),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            source = target.with_suffix('.png')
        languages = (
            subprocess.run(
                [executable, '--list-langs'], capture_output=True, check=True, timeout=5
            )
            .stdout.decode()
            .splitlines()
        )
        selected = '+'.join(
            language for language in ('fra', 'eng', 'deu') if language in languages
        )
        if not selected:
            raise ValueError('ocr_unavailable')
        result = subprocess.run(
            [executable, str(source), 'stdout', '-l', selected, '--psm', '3'],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return result.stdout.decode('utf-8')


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    except (ValueError, OSError):
        pass  # Some macOS versions do not implement address-space limits.
    data = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Oversized PDF')
    if not data.startswith(b'%PDF-'):
        suffix = (
            '.png'
            if data.startswith(b'\x89PNG\r\n\x1a\n')
            else '.jpg' if data.startswith(b'\xff\xd8\xff') else ''
        )
        if not suffix:
            raise ValueError('Invalid image')
        text = ocr(data, suffix)
        if len(text) > 16000:
            raise ValueError('Excessive text')
        print(json.dumps({'text': text, 'ocr': True}))
        return
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > 30:
        raise ValueError('Encrypted or excessive page count')
    remaining = 16000
    chunks = []
    used_ocr = False
    for index, page in enumerate(reader.pages):
        if remaining <= 0:
            raise ValueError('Excessive text')
        chunk = page.extract_text() or ''
        if sum(c.isalnum() for c in chunk) < 30 and page.get('/Contents'):
            chunk = ocr(data, '.pdf', index)
            used_ocr = True
        if len(chunk) > remaining:
            raise ValueError('Excessive text')
        chunks.append(chunk)
        remaining -= len(chunk) + 1
    print(json.dumps({'text': '\n'.join(chunks).strip(), 'ocr': used_ocr}))


if __name__ == '__main__':
    main()
