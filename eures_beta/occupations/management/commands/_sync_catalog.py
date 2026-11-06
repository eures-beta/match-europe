import json
from pathlib import Path

import requests

from django.core.management.base import BaseCommand, CommandError

from eures_beta.occupations.tools.refresh_catalog import refresh


class SyncCatalogCommand(BaseCommand):
    requires_system_checks = []
    kind = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', type=Path, default=Path('.runtime/catalog-staging')
        )
        parser.add_argument('--allow-removals', action='store_true')
        if self.kind in ('esco', 'rome'):
            parser.add_argument('--source-version')
        if self.kind in ('rome', 'mapping'):
            parser.add_argument('--source-url')

    def handle(self, **options):
        try:
            report = refresh(
                self.kind,
                options['output'],
                version=options.get('source_version'),
                source_url=options.get('source_url'),
                allow_removals=options['allow_removals'],
            )
        except (ValueError, OSError, KeyError, requests.RequestException) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {
                    key: {
                        field: len(value) if isinstance(value, list) else value
                        for field, value in changes.items()
                    }
                    for key, changes in report.items()
                },
                ensure_ascii=False,
            )
        )
        self.stdout.write(
            f"Prepared JSON and update-report.json in {options['output']}; review before publication."
        )
