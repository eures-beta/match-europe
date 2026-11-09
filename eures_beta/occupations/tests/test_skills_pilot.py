from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from eures_beta.occupations.skills_pilot import catalogue


class RetiredPilotTests(SimpleTestCase):
    def test_retired_routes_are_not_registered(self):
        for path in (
            '/skills-pilot/',
            '/skills-pilot/employer/',
            '/skills-pilot/candidate/',
        ):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)

    def test_shared_catalogue_remains_available(self):
        cards, skills = catalogue()
        self.assertEqual(len(cards), 50)
        self.assertTrue(skills)
