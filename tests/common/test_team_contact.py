"""Changing the shared address updates every public team contact."""

from django.test import SimpleTestCase, override_settings
from django.template.loader import render_to_string
from django.test import RequestFactory

from eures_beta.www.contact import context


@override_settings(TEAM_CONTACT_EMAIL='team@example.invalid')
class TeamContactTests(SimpleTestCase):
    def test_shared_address_reaches_feedback_notice_and_privacy_templates(self):
        request = RequestFactory().get('/')
        values = {**context(request), 'step': 2}
        for template in (
            'candidates/feedback.html',
            'employer/development_notice.html',
            'data_protection.html',
            'invitations/includes/employer_invitation_help.html',
        ):
            with self.subTest(template=template):
                html = render_to_string(template, values)
                self.assertIn('mailto:team@example.invalid', html)
                self.assertNotIn('eric.barthelemy@francetravail.fr', html)
