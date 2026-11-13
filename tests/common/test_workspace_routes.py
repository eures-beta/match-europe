from django.test import Client, SimpleTestCase
from django.urls import resolve, reverse

from eures_beta.www.adviser import matching as adviser_matching
from eures_beta.www.matching import views as matching_views


class WorkspaceRouteTests(SimpleTestCase):
    def test_matching_interfaces_remain_distinct(self):
        self.assertEqual(reverse('adviser_match', args=[12]), '/matching/12/review/')
        self.assertEqual(reverse('matching_detail', args=[12]), '/matching/12/')
        self.assertIs(resolve('/matching/12/review/').func, adviser_matching.detail)
        self.assertIs(resolve('/matching/12/').func, matching_views.detail)

    def test_canonical_invitations_and_employer_profile(self):
        self.assertEqual(reverse('adviser_invitations'), '/adviser/invitations/')
        self.assertEqual(reverse('employer_invite'), '/adviser/invitations/new/')
        self.assertEqual(
            reverse('invitation_confirm'), '/accounts/invitations/confirm/'
        )
        self.assertEqual(
            reverse('employer_response_practice'), '/api/employer/profile/'
        )

    def test_legacy_requests_keep_their_method_body_and_query(self):
        for old, new in (
            ('/accounts/dashboard/matching/12/', '/matching/12/review/'),
            ('/accounts/dashboard/invitations/', '/adviser/invitations/'),
            ('/accounts/employers/invite/', '/adviser/invitations/new/'),
            ('/api/employer/response-practice/', '/api/employer/profile/'),
        ):
            for method in ('get', 'head', 'post'):
                with self.subTest(old=old, method=method):
                    response = getattr(self.client, method)(
                        old + '?lang=de&source=bookmark'
                    )
                    self.assertEqual(response.status_code, 308)
                    self.assertEqual(
                        response['Location'], new + '?lang=de&source=bookmark'
                    )

    def test_old_post_does_not_bypass_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post('/accounts/employers/invite/', {}).status_code, 403
        )
        self.assertEqual(
            client.post('/api/employer/response-practice/', {}).status_code, 403
        )
