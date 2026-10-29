"""Offline integrity, coverage and search regressions for the vendored data."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from eures_beta.occupations import catalog as service


class OccupationCatalogTests(SimpleTestCase):
    def test_complete_multilingual_catalog_and_rome_coverage_without_network(self):
        service.catalog.cache_clear()
        service.rome_catalog.cache_clear()
        with patch(
            'socket.socket.connect', side_effect=AssertionError('Unexpected network')
        ):
            data = service.catalog()
            rome = service.rome_catalog()
            self.assertEqual(data['manifest']['version'], '1.2.1')
            self.assertEqual(len(data['occupations']), 3039)
            self.assertEqual(len(rome['fiches']), 1923)
            self.assertEqual(len(rome['appellations']), 14330)
            self.assertEqual(len(rome['mappings']), 13120)
            for row in data['occupations']:
                for language in ('fr', 'en', 'de'):
                    self.assertTrue(row['labels'][language].strip())
                    self.assertTrue(row['descriptions'][language].strip())
            for query, language, expected in (
                ('bibliothécaire', 'fr', 'biblioth'),
                ('orthophoniste', 'fr', 'orthophon'),
                ('pharmacien', 'fr', 'pharmac'),
                ('architect', 'en', 'architect'),
                ('psychologist', 'en', 'psycholog'),
                ('Bäcker', 'de', 'back'),
                ('Bibliothekar', 'de', 'bibliothek'),
            ):
                results = service.suggestions(query, language)
                self.assertTrue(results, (query, language))
                self.assertTrue(
                    any(expected in service.normalize(row['label']) for row in results),
                    results,
                )
            self.assertEqual(service.suggestions('xyzqzzzz', 'fr'), [])

    def test_no_invented_mapping_and_unresolved_source_ids_are_reported(self):
        data = service.catalog()
        rome = service.rome_catalog()
        stats = data['manifest']['counts']
        self.assertEqual(
            sum(bool(row['romeFiches']) for row in data['occupations']), 2046
        )
        self.assertEqual(len(stats['unresolvedRomeAppellationIds']), 22)
        for row in data['occupations']:
            if not row['rome']:
                self.assertEqual(row['romeFiches'], [])
            for match in row['rome']:
                self.assertEqual(
                    match['ficheCodes'],
                    rome['appellations'].get(match['id'], {}).get('ficheCodes', []),
                )
        self.assertEqual(stats['esco_fr_sourceRows'], 3043)
        self.assertEqual(stats['esco_fr_duplicateRows'], 4)
        self.assertEqual(stats['mappingUrisAbsentFromEsco'], 4)

    def test_corrupt_snapshot_fails_instead_of_using_network_or_silent_fallback(self):
        manifest = (service.DATA_DIR / 'manifest.json').read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'manifest.json').write_text(manifest)
            (path / 'occupations.json.gz').write_bytes(b'corrupt')
            service.catalog.cache_clear()
            try:
                with patch.object(service, 'DATA_DIR', path):
                    with self.assertRaisesRegex(ValueError, 'checksum'):
                        service.catalog()
            finally:
                service.catalog.cache_clear()

    def test_baker_is_first_and_nearby_does_not_mix_retail_management(self):
        results = service.suggestions('boulanger', 'fr')
        self.assertEqual(results[0]['label'], 'boulanger/boulangère')
        nearby = service.nearby('boulanger', 'fr', [row['uri'] for row in results])
        self.assertTrue(nearby)
        self.assertFalse(
            {row['uri'] for row in nearby} & {row['uri'] for row in results}
        )
        self.assertFalse(any('tabac' in row['label'] for row in nearby))

    def test_typo_tolerance_and_unsupported_language(self):
        self.assertTrue(service.suggestions('bibliothecair', 'fr'))
        with self.assertRaises(ValueError):
            service.suggestions('baker', 'xx')
