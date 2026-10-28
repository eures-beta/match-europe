import json
import secrets
import subprocess
import sys
from pathlib import Path
from django.utils.translation import gettext_lazy as _
from eures_beta.documents.models import Document
from eures_beta.accounts.services import audit


def extract_pdf(upload, user):
    contents = upload.read()
    if len(contents) > 10 * 1024 * 1024:
        raise ValueError(_('The PDF must be smaller than 10 MB.'))
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().parents[1] / 'documents' / 'pdf_reader.py'
                ),
            ],
            input=contents,
            capture_output=True,
            timeout=15,
            check=True,
        )
        text = json.loads(result.stdout)['text']
    except Exception as exc:
        raise ValueError(
            _(
                'This PDF cannot be read. Use an unencrypted document with at most 30 pages.'
            )
        ) from exc
    upload.seek(0)
    # Never serve the original filename or execute embedded PDF content.
    upload.name = secrets.token_hex(16) + '.pdf'
    document = Document.objects.create(owner=user, file=upload, text=text)
    audit(user, 'pdf_uploaded', document)
    return document
