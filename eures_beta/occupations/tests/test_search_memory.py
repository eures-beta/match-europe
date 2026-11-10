"""A cold public search must leave room for the rest of the web worker."""

from django.test import SimpleTestCase

from eures_beta.occupations.tools.benchmark_memory import measure


class SearchMemoryTests(SimpleTestCase):
    def test_cold_independent_search_stays_below_memory_budget(self):
        report = measure()
        self.assertLess(report['peak_mib'], 145, report)
