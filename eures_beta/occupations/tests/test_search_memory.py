"""A cold public search must leave room for the rest of the web worker."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from unittest.mock import patch

from django.test import SimpleTestCase

from eures_beta.occupations import catalog as service
from eures_beta.occupations.tools.benchmark_memory import measure


class SearchMemoryTests(SimpleTestCase):
    def test_cold_independent_search_stays_below_memory_budget(self):
        report = measure()
        self.assertLess(report['peak_mib'], 145, report)

    def test_streamed_catalog_preserves_every_source_field(self):
        manifest = json.loads((service.DATA_DIR / 'manifest.json').read_text())
        for name in ('esco.json', 'rome.json', 'ogr.json', 'esco_rome.json'):
            path = service.DATA_DIR / name
            with self.subTest(name=name):
                self.assertEqual(
                    service.read_artifact(path, manifest), json.loads(path.read_bytes())
                )

    def test_concurrent_cold_searches_load_each_needed_file_only_once(self):
        for function in (
            service.catalog,
            service.occupation_index,
            service.search_index,
            service.rome_search_catalog,
        ):
            function.cache_clear()
        ready = Barrier(8)

        def search(_):
            ready.wait(timeout=10)
            return (
                service.suggestions(
                    'électricien industriel', 'fr', 'maintenance électrique'
                ),
                service.rome_suggestions('électricien industriel'),
            )

        with patch.object(
            service, 'read_artifact', wraps=service.read_artifact
        ) as read:
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(search, range(8)))
            self.assertTrue(all(value == results[0] for value in results))
            self.assertTrue(results[0][0])
            self.assertTrue(results[0][1])
            self.assertCountEqual(
                [call.args[0].name for call in read.call_args_list],
                ['esco.json', 'rome.json', 'ogr.json'],
            )

    def test_validating_selected_rome_jobs_reuses_the_search_catalog(self):
        from eures_beta.candidates.occupation_choices import resolve_reference
        from eures_beta.employers.occupation_selection import clean_selection

        code = next(iter(service.rome_search_catalog()['fiches']))
        with patch.object(
            service, 'read_artifact', side_effect=AssertionError('Reload')
        ):
            self.assertIsNotNone(resolve_reference('rome:' + code, 'fr'))
            selected = clean_selection(
                {
                    'title': 'Test métier',
                    'version': service.catalog()['manifest']['version'],
                    'rome_codes': [code],
                },
                'Test métier',
            )
            self.assertEqual(selected['rome_jobs'][0]['code'], code)
