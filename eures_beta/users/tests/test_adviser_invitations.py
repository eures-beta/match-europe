from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates import journey
from eures_beta.candidates.tests.test_registration import answers
from eures_beta.users.invitations import find_invitation, invitation_token
from eures_beta.users.models import EmployerInvitation, User


class AdviserInvitationsTests(TestCase):
    def setUp(self):
        self.adviser = User.objects.create_superuser(
            'admin@example.invalid', kind=User.Kind.ADVISER
        )
        self.client.force_login(self.adviser)
        self.tab = reverse('adviser_invitations')

    def test_dashboard_opens_invite_and_preserves_language(self):
        dashboard = reverse('dashboard')
        response = self.client.get(dashboard, {'lang': 'en'})
        self.assertContains(response, 'aria-current="page">Inviter')
        self.assertContains(response, '?lang=en&amp;mode=csv')
        self.assertRedirects(
            self.client.get(self.tab, {'lang': 'en', 'mode': 'csv'}),
            dashboard + '?lang=en&mode=csv',
        )

    def preview(self, audience, email='person@example.invalid'):
        return self.client.post(
            self.tab,
            {
                'action': 'preview',
                'audience': audience,
                'email': email,
                'first_name': 'Camille',
            },
        )

    def test_employer_preview_uses_connected_adviser_signature_and_partner_logos(self):
        self.adviser.first_name = 'Lou'
        self.adviser.adviser_organisation = 'Structure & partenaires'
        self.adviser.save(update_fields=['first_name', 'adviser_organisation'])

        response = self.preview('employer')
        preview = response.context['previews'][0]
        self.assertEqual(preview['subject'], 'MATCH EUROPE : votre lien d’accès')
        self.assertIn('Suite à nos échanges', preview['html'])
        self.assertIn('Lou', preview['html'])
        self.assertIn('Structure &amp; partenaires', preview['html'])
        for filename in (
            'eures-ela.jpg',
            'france-travail-email.png',
            'adem.png',
            'forem.png',
        ):
            self.assertIn(filename, preview['html'])

    def test_candidate_preview_delivery_and_acceptance(self):
        with (
            TemporaryDirectory() as directory,
            override_settings(
                DEBUG=True,
                BASE_DIR=Path(directory),
                LOGIN_EMAIL_ORIGIN='http://127.0.0.1:9060',
                ALLOWED_HOSTS=['testserver', '127.0.0.1'],
                DJANGO_ENVIRONMENT='local',
                EMAIL_DELIVERY_ENABLED=False,
            ),
        ):
            response = self.preview('candidate')
            self.assertContains(response, 'Bonjour Camille')
            self.assertContains(response, 'srcdoc="&lt;!')
            self.assertFalse(EmployerInvitation.objects.exists())
            self.assertRedirects(
                self.client.post(
                    self.tab,
                    {'action': 'send', 'preview': response.context['preview_token']},
                ),
                reverse('dashboard') + '?lang=fr',
            )
            invitation = EmployerInvitation.objects.get()
            self.assertIsNotNone(invitation.email_sent_at)
            files = list((Path(directory) / '.runtime/invitation-outbox').glob('*.log'))
            self.assertEqual(len(files), 1)
            self.assertIn('text/html', files[0].read_text())
            self.assertIn('text/plain', files[0].read_text())
            self.client.logout()
            url = reverse('employer_invitation_confirm')
            self.client.get(url, {'invitation': invitation_token(invitation)})
            self.assertRedirects(self.client.post(url), reverse('candidate_prepare'))
            invitation.refresh_from_db()
            self.assertIsNotNone(invitation.accepted_at)
            self.assertEqual(invitation.employer.kind, User.Kind.CANDIDATE)
            self.assertEqual(invitation.employer.first_name, 'Camille')
            self.assertRedirects(
                self.client.get(reverse('dashboard')), reverse('candidate_prepare')
            )
            session = self.client.session
            session[journey.KEY] = {
                'schema': journey.SCHEMA,
                'created_at': time(),
                'token': 'test-draft',
                'unlocked': 4,
                'data': answers(),
            }
            session.save()
            destination = reverse('candidate_prepare') + '?step=4'
            self.assertTrue(
                self.client.get(destination)
                .context['form']
                .fields['contact_email']
                .disabled
            )
            self.assertRedirects(
                self.client.post(
                    destination,
                    {
                        'action': 'finish',
                        'token': 'test-draft',
                        'reviewed': 'on',
                        'display_name': 'Camille',
                        'contact_email': 'other@example.invalid',
                    },
                ),
                reverse('candidate_profile'),
            )
            profile = invitation.employer.candidate_profile
            self.assertEqual(profile.display_name, 'Camille')
            self.assertIsNotNone(profile.notice_read_at)
            self.assertFalse(
                User.objects.filter(email='other@example.invalid').exists()
            )

    def test_csv_only_requires_email_and_reports_invalid_rows(self):
        def upload(content):
            return self.client.post(
                self.tab,
                {
                    'action': 'import',
                    'audience': 'employer',
                    'csv': SimpleUploadedFile('contacts.csv', content),
                },
            )

        response = upload(b'email\na@example.invalid\nb@example.invalid\n')
        self.assertEqual(len(response.context['previews']), 2)
        self.assertFalse(EmployerInvitation.objects.exists())
        response = upload(
            b'email;nom\na@example.invalid;A\nA@example.invalid;B\ninvalid;C\n'
        )
        self.assertContains(response, 'Ligne 3')
        self.assertContains(response, 'Ligne 4')
        self.assertNotIn('previews', response.context)

    def test_relaunch_and_removal_revoke_links(self):
        invitation = EmployerInvitation.objects.create(
            email='employer@example.invalid',
            invited_by=self.adviser,
            email_sent_at=timezone.now() - timedelta(hours=2),
        )
        initial_token = invitation_token(invitation)
        response = self.client.post(
            self.tab, {'action': 'preview_reminder', 'invitation': invitation.pk}
        )
        with (
            TemporaryDirectory() as directory,
            override_settings(
                DEBUG=True,
                BASE_DIR=Path(directory),
                LOGIN_EMAIL_ORIGIN='http://127.0.0.1:9060',
                ALLOWED_HOSTS=['testserver', '127.0.0.1'],
                DJANGO_ENVIRONMENT='local',
                EMAIL_DELIVERY_ENABLED=False,
            ),
        ):
            self.client.post(
                self.tab,
                {'action': 'send', 'preview': response.context['preview_token']},
            )
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.reminder_sent_at)
        self.assertIsNone(find_invitation(initial_token))
        new_token = invitation_token(invitation)
        self.assertIsNotNone(find_invitation(new_token))
        self.client.post(self.tab, {'action': 'remove', 'invitation': invitation.pk})
        self.assertIsNone(find_invitation(new_token))

    def test_authorized_adviser_can_invite_without_granting_staff(self):
        regular = User.objects.create_user(
            'regular@example.invalid', kind=User.Kind.ADVISER
        )
        self.client.force_login(regular)
        page = self.client.get(reverse('dashboard'))
        self.assertContains(page, 'value="adviser"')
        self.assertNotContains(page, 'Consulter les comptes employeurs')
        response = self.preview('adviser')
        self.assertContains(response, 'Rejoignez l’équipe')
        self.client.post(
            self.tab, {'action': 'send', 'preview': response.context['preview_token']}
        )
        invitation = EmployerInvitation.objects.get()
        self.client.logout()
        url = reverse('employer_invitation_confirm')
        self.client.get(url, {'invitation': invitation_token(invitation)})
        self.client.post(url)
        invited = User.objects.get(email=invitation.email)
        self.assertEqual(invited.kind, User.Kind.ADVISER)
        self.assertFalse(invited.is_staff)
