from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.www.candidate import journey
from tests.candidates.test_registration import answers
from eures_beta.invitations.services import find_invitation, invitation_token
from eures_beta.invitations.models import Invitation
from eures_beta.users.models import User


class AdviserInvitationsTests(TestCase):
    def setUp(self):
        self.adviser = User.objects.create_superuser(
            'admin@example.invalid', kind=User.Kind.ADVISER
        )
        self.client.force_login(self.adviser)
        self.tab = reverse('adviser_invitations')

    def test_invite_tab_preserves_language(self):
        dashboard = reverse('dashboard')
        response = self.client.get(dashboard, {'lang': 'en', 'tab': 'invite'})
        self.assertContains(response, 'aria-current="page">Invite')
        self.assertContains(response, '?tab=invite&amp;lang=en&amp;mode=csv')
        self.assertRedirects(
            self.client.get(self.tab, {'lang': 'en', 'mode': 'csv'}),
            dashboard + '?lang=en&mode=csv&tab=invite',
        )

    def test_history_requires_selecting_tracking(self):
        dashboard = reverse('dashboard')
        create = self.client.get(dashboard, {'tab': 'invite'})
        self.assertContains(create, 'id="compose-title"')
        self.assertNotContains(create, 'id="history-title"')
        history = self.client.get(dashboard, {'tab': 'invite', 'view': 'history'})
        self.assertContains(history, 'id="history-title"')
        self.assertNotContains(history, 'id="compose-title"')

    def test_history_distinguishes_initial_email_and_last_reminder(self):
        initial = datetime(2026, 1, 10, 8, 17, tzinfo=UTC)
        reminder = datetime(2026, 1, 12, 10, 23, tzinfo=UTC)
        Invitation.objects.create(
            email='reminded@example.invalid',
            sender_adviser=self.adviser,
            email_sent_at=initial,
            reminder_sent_at=reminder,
        )
        Invitation.objects.create(
            email='unreminded@example.invalid',
            sender_adviser=self.adviser,
            email_sent_at=initial,
        )
        dashboard = reverse('dashboard')
        with timezone.override(UTC):
            history = self.client.get(
                dashboard, {'tab': 'invite', 'view': 'history', 'lang': 'fr'}
            )
        self.assertContains(history, '<th scope="col">Envoi initial</th>', html=True)
        self.assertContains(history, '<th scope="col">Dernière relance</th>', html=True)
        self.assertContains(
            history, '<td>10/01/2026 08:17</td> <td>12/01/2026 10:23</td>', html=True
        )
        self.assertContains(history, '<td>10/01/2026 08:17</td> <td>—</td>', html=True)

    def preview(self, recipient_kind, email='person@example.invalid'):
        return self.client.post(
            self.tab,
            {
                'action': 'preview',
                'recipient_kind': recipient_kind,
                'email': email,
                'first_name': 'Camille',
            },
        )

    def test_employer_preview_uses_connected_adviser_signature_and_partner_logos(self):
        self.adviser.first_name = 'Lou'
        self.adviser.organization_name = 'Structure & partenaires'
        self.adviser.save(update_fields=['first_name', 'organization_name'])

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

    def test_candidate_delivery_keeps_preview_language(self):
        from unittest.mock import patch
        from django.test import RequestFactory
        from eures_beta.www.invitations.adviser import send_batch

        request = RequestFactory().post(self.tab)
        request.user = self.adviser
        with (
            patch('eures_beta.www.invitations.adviser.deliver', return_value=True),
            patch('eures_beta.www.invitations.adviser.messages.success'),
        ):
            send_batch(
                request,
                {
                    'recipient_kind': 'candidate',
                    'language': 'de',
                    'recipients': [
                        {
                            'email': 'candidate@example.invalid',
                            'first_name': 'Camille',
                            'last_name': '',
                        }
                    ],
                },
            )
        self.assertEqual(Invitation.objects.get().language, 'de')

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
            self.assertContains(response, 'Bonjour,')
            self.assertNotContains(response, 'Bonjour Camille')
            self.assertContains(response, 'srcdoc="&lt;!')
            self.assertFalse(Invitation.objects.exists())
            self.assertRedirects(
                self.client.post(
                    self.tab,
                    {'action': 'send', 'preview': response.context['preview_token']},
                ),
                reverse('dashboard') + '?lang=fr&tab=invite',
            )
            invitation = Invitation.objects.get()
            self.assertIsNotNone(invitation.email_sent_at)
            files = list((Path(directory) / '.runtime/invitation-outbox').glob('*.log'))
            self.assertEqual(len(files), 1)
            self.assertIn('text/html', files[0].read_text())
            self.assertIn('text/plain', files[0].read_text())
            self.client.logout()
            url = reverse('invitation_confirm')
            self.client.get(url, {'invitation': invitation_token(invitation)})
            self.assertRedirects(self.client.post(url), reverse('candidate_prepare'))
            invitation.refresh_from_db()
            self.assertIsNotNone(invitation.accepted_at)
            self.assertEqual(invitation.recipient.kind, User.Kind.CANDIDATE)
            self.assertEqual(invitation.recipient.first_name, 'Camille')
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
            profile = invitation.recipient.candidate_profile
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
                    'recipient_kind': 'employer',
                    'csv': SimpleUploadedFile('contacts.csv', content),
                },
            )

        response = upload(b'email\na@example.invalid\nb@example.invalid\n')
        self.assertEqual(len(response.context['previews']), 2)
        self.assertFalse(Invitation.objects.exists())
        response = upload(
            b'email;nom\na@example.invalid;A\nA@example.invalid;B\ninvalid;C\n'
        )
        self.assertContains(response, 'Ligne 3')
        self.assertContains(response, 'Ligne 4')
        self.assertNotIn('previews', response.context)

    def test_relaunch_and_removal_revoke_links(self):
        invitation = Invitation.objects.create(
            email='employer@example.invalid',
            sender_adviser=self.adviser,
            email_sent_at=timezone.now() - timedelta(hours=25),
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
        page = self.client.get(reverse('dashboard'), {'tab': 'invite'})
        self.assertContains(page, 'value="adviser"')
        self.assertNotContains(page, 'Consulter les comptes employeurs')
        response = self.preview('adviser')
        self.assertContains(response, 'Rejoignez l’équipe')
        self.client.post(
            self.tab, {'action': 'send', 'preview': response.context['preview_token']}
        )
        invitation = Invitation.objects.get()
        self.client.logout()
        url = reverse('invitation_confirm')
        self.client.get(url, {'invitation': invitation_token(invitation)})
        self.client.post(url)
        invited = User.objects.get(email=invitation.email)
        self.assertEqual(invited.kind, User.Kind.ADVISER)
        self.assertFalse(invited.is_staff)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('eures_beta.www.invitations.adviser.email_ready', return_value=True)
    @override_settings(
        LOGIN_EMAIL_ORIGIN='https://example.invalid',
        ALLOWED_HOSTS=['testserver', 'example.invalid'],
    )
    def test_fifteen_individual_sends_and_replayed_confirmation(self, ready):
        for index in range(15):
            preview = self.preview('candidate', f'person{index}@example.invalid')
            payload = {'action': 'send', 'preview': preview.context['preview_token']}
            self.client.post(self.tab, payload)
        self.client.post(self.tab, payload)
        self.assertEqual(Invitation.objects.count(), 15)
        self.assertEqual(len(mail.outbox), 15)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        LOGIN_EMAIL_ORIGIN='https://example.invalid',
        ALLOWED_HOSTS=['testserver', 'example.invalid'],
    )
    @patch('eures_beta.www.invitations.adviser.email_ready', return_value=True)
    def test_csv_accepts_and_sends_more_than_ten_recipients(self, ready):
        content = 'email\n' + ''.join(f'person{i}@example.invalid\n' for i in range(15))
        response = self.client.post(
            self.tab,
            {
                'action': 'import',
                'recipient_kind': 'candidate',
                'csv': SimpleUploadedFile('contacts.csv', content.encode()),
            },
        )
        self.assertEqual(len(response.context['previews']), 15)
        self.assertFalse(Invitation.objects.exists())
        payload = {'action': 'send', 'preview': response.context['preview_token']}
        result = self.client.post(self.tab, payload, follow=True)
        self.assertEqual(
            Invitation.objects.filter(email_sent_at__isnull=False).count(), 15
        )
        self.assertEqual(len(mail.outbox), 15)
        for index in range(15):
            self.assertContains(result, f'person{index}@example.invalid')
        self.client.post(self.tab, payload)
        self.assertEqual(len(mail.outbox), 15)

    @patch('eures_beta.www.invitations.adviser.deliver', return_value=True)
    def test_reminder_cooldown_and_replayed_confirmation(self, deliver):
        now = timezone.now()
        invitation = Invitation.objects.create(
            email='reminder@example.invalid',
            sender_adviser=self.adviser,
            email_sent_at=now - timedelta(days=2),
            reminder_sent_at=now - timedelta(hours=23),
        )
        original_nonce = invitation.nonce
        response = self.client.post(
            self.tab, {'action': 'preview_reminder', 'invitation': invitation.pk}
        )
        payload = {'action': 'send', 'preview': response.context['preview_token']}
        blocked = self.client.post(self.tab, payload)
        self.assertContains(blocked, '24')
        deliver.assert_not_called()
        invitation.refresh_from_db()
        self.assertEqual(invitation.nonce, original_nonce)
        invitation.reminder_sent_at = now - timedelta(hours=24)
        invitation.save(update_fields=['reminder_sent_at'])
        self.client.post(self.tab, payload)
        self.client.post(self.tab, payload)
        self.assertEqual(deliver.call_count, 1)

    @patch('eures_beta.www.invitations.adviser.deliver', return_value=False)
    def test_failed_delivery_is_explicit_and_saved_without_sent_date(self, deliver):
        preview = self.preview('candidate')
        response = self.client.post(
            self.tab,
            {
                'action': 'send',
                'preview': preview.context['preview_token'],
            },
            follow=True,
        )
        invitation = Invitation.objects.get()
        self.assertIsNone(invitation.email_sent_at)
        self.assertContains(response, invitation.email)
        self.assertContains(response, 'non envoyé')

    @patch('eures_beta.www.invitations.adviser.deliver', return_value=True)
    def test_initial_send_starts_reminder_delay_but_unsent_retry_is_allowed(
        self, deliver
    ):
        invitation = Invitation.objects.create(
            email='retry@example.invalid',
            sender_adviser=self.adviser,
            email_sent_at=timezone.now(),
        )
        preview = self.client.post(
            self.tab, {'action': 'preview_reminder', 'invitation': invitation.pk}
        )
        payload = {'action': 'send', 'preview': preview.context['preview_token']}
        self.client.post(self.tab, payload)
        deliver.assert_not_called()
        invitation.email_sent_at = None
        invitation.save(update_fields=['email_sent_at'])
        self.client.post(self.tab, payload)
        deliver.assert_called_once()
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.email_sent_at)
        self.assertIsNone(invitation.reminder_sent_at)

    def test_csv_file_size_guard_is_preserved(self):
        response = self.client.post(
            self.tab,
            {
                'action': 'import',
                'recipient_kind': 'candidate',
                'csv': SimpleUploadedFile(
                    'contacts.csv', b'email\n' + b'x' * (64 * 1024)
                ),
            },
        )
        self.assertContains(response, '64 Ko')
        self.assertNotIn('previews', response.context)


class CandidateInvitationContentTests(SimpleTestCase):
    def render(self, language='fr', name='Lou', organization='France Travail'):
        from types import SimpleNamespace
        from eures_beta.www.invitations.adviser import render_message

        return render_message(
            'candidate',
            {'first_name': 'Recipient', 'last_name': 'Private'},
            'https://example.invalid',
            'https://example.invalid/invitation/?invitation=fictional-token',
            adviser=SimpleNamespace(
                get_full_name=lambda: name, organization_name=organization
            ),
            language=language,
        )

    def test_invitation_languages_links_signature_and_brand(self):
        for language, subject, greeting, intro, cta in (
            (
                'fr',
                'EURES – Des opportunités d’emploi en Europe',
                'Bonjour,',
                'Je suis Lou, conseiller France Travail au sein du réseau européen EURES.',
                'Voir si mon profil correspond',
            ),
            (
                'en',
                'EURES – Job opportunities in Europe',
                'Hello,',
                'I am Lou, an adviser at France Travail within the European EURES network.',
                'See if my profile matches',
            ),
            (
                'de',
                'EURES – Beschäftigungsmöglichkeiten in Europa',
                'Guten Tag,',
                'Ich bin Lou, Berater bei France Travail im europäischen EURES-Netzwerk.',
                'Prüfen, ob mein Profil passt',
            ),
        ):
            with self.subTest(language=language):
                actual, text, html = self.render(language)
                self.assertEqual(actual, subject)
                for content in (text, html):
                    for expected in (
                        greeting,
                        intro,
                        cta,
                        'https://example.invalid/privacy/',
                        'https://example.invalid/invitation/?invitation=fictional-token',
                    ):
                        self.assertIn(expected, content)
                    self.assertNotIn('Recipient', content)
                    self.assertNotIn('Private', content)
                self.assertIn('lang="' + language + '"', html)
                for asset in (
                    'eures-ela.jpg',
                    'france-travail-email.png',
                    'adem.png',
                    'forem.png',
                ):
                    self.assertIn(asset, html)
                self.assertIn('alt="France Travail"', html)

    def test_real_identity_is_escaped_and_missing_data_is_not_invented(self):
        _, text, html = self.render(
            name='<script>alert(1)</script>', organization='ADEM & partenaires'
        )
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('ADEM &amp; partenaires', html)
        self.assertIn('conseiller ADEM & partenaires', text)
        self.assertNotIn('conseiller France Travail', text)
        _, text, html = self.render(name='', organization='')
        self.assertIn('au nom de l’équipe Match Europe', text)
        self.assertNotIn('Je suis', text)
        self.assertNotIn('Conseiller EURES – France Travail', text)
        _, text, _ = self.render(organization='')
        self.assertIn('Je suis Lou, conseiller au sein du réseau européen EURES.', text)
        self.assertNotIn('conseiller France Travail', text)
