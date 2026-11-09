"""Explicit real-call evaluation of an operator-supplied local text, never a fixture."""

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from eures_beta.employers.offer_structuring import structure, enabled
from eures_beta.employers.offer_ingestion import ImportFailure, read_pdf
from eures_beta.occupations.catalog import suggestions, rome_suggestions


class Command(BaseCommand):
    help = 'Structure a local text with Albert and record references for manual evaluation.'

    def add_arguments(self, parser):
        parser.add_argument('source')
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        if not enabled():
            raise CommandError('Albert is disabled in this environment.')
        path = Path(options['source'])
        if path.stat().st_size > 10 * 1024 * 1024:
            raise CommandError('Source too large.')
        if path.suffix.lower() == '.pdf':
            try:
                source = read_pdf(
                    SimpleUploadedFile(path.name, path.read_bytes()), include_text=True
                )['_sourceText']
            except ImportFailure as exc:
                raise CommandError(exc.code) from None
        else:
            source = path.read_text()
        started = time.monotonic()
        try:
            data = structure(source)
        except ImportFailure as exc:
            raise CommandError(exc.code) from None
        context = data['description'] + '\n' + data['desiredProfile']
        query = data['occupationQuery']
        result = {
            'duration_seconds': round(time.monotonic() - started, 2),
            'data': data,
            'esco': suggestions(query, 'fr', context),
            'rome': rome_suggestions(query, context),
        }
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        output.chmod(0o600)
        self.stdout.write(
            'Evaluation saved; verify every field and proposed reference.'
        )
