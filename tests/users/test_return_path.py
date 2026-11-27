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
