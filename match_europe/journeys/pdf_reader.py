"""Bounded PDF text extraction in a separate process. Never execute PDF actions."""
import io
import json
import resource
import sys

from pypdf import PdfReader


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    except (ValueError, OSError):
        pass  # Some macOS versions do not implement address-space limits.
    data = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Oversized PDF')
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > 30:
        raise ValueError('Encrypted or excessive page count')
    remaining = 16000
    chunks = []
    for page in reader.pages:
        if remaining <= 0:
            break
        chunk = (page.extract_text() or '')[:remaining]
        chunks.append(chunk)
        remaining -= len(chunk) + 1
    print(json.dumps({'text': '\n'.join(chunks).strip()}))


if __name__ == '__main__':
    main()
