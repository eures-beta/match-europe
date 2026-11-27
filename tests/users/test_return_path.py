from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from eures_beta.www.accounts.return_path import consume


class ReturnPathRoleTests(SimpleTestCase):
    def test_destinations_require_the_connected_role_and_are_consumed(self):
        destinations = (
            (reverse('employer_import'), 'employer'),
            (reverse('candidate_offer_dialogue', args=[123]), 'candidate'),
        )
        for path, expected_kind in destinations:
            for kind in ('adviser', 'employer', 'candidate'):
                with self.subTest(path=path, kind=kind):
                    user = SimpleNamespace(
                        is_authenticated=True, is_active=True, kind=kind
                    )
                    request = SimpleNamespace(
                        user=user, session={'login_return_path': path}
                    )
                    self.assertEqual(
                        consume(request, '/accounts/dashboard/'),
                        path if kind == expected_kind else '/accounts/dashboard/',
                    )
                    self.assertNotIn('login_return_path', request.session)

    def test_confirmation_uses_the_new_account_not_the_previous_session_user(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True, is_active=True, kind='employer'
            ),
            session={'login_return_path': reverse('employer_import')},
        )
        adviser = SimpleNamespace(is_authenticated=True, is_active=True, kind='adviser')
        self.assertEqual(
            consume(request, '/accounts/dashboard/', user=adviser),
            '/accounts/dashboard/',
        )


class PlanningReturnPathTests(SimpleTestCase):
    def test_only_active_staff_can_return_to_planning_regardless_of_role(self):
        from eures_beta.www.accounts.return_path import canonical_destination

        path = reverse('staff_planning', query={'lang': 'fr', 'week': '2026-11-23'})
        self.assertEqual(canonical_destination(path), path)
        for role in ('candidate', 'employer', 'adviser'):
            for staff in (False, True):
                user = SimpleNamespace(
                    is_authenticated=True, is_active=True, is_staff=staff, kind=role
                )
                request = SimpleNamespace(
                    user=user, session={'login_return_path': path}
                )
                self.assertEqual(consume(request, '/'), path if staff else '/')
        for suffix in (
            '?week=invalid',
            '?week=20261123',
            '?week=2026-11-23&week=2026-11-30',
            '?next=https://evil.invalid',
            '?lang=es',
        ):
            self.assertEqual(
                canonical_destination(reverse('staff_planning') + suffix), ''
            )
