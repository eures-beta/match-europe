from datetime import timedelta
from io import StringIO
import logging
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command, CommandError
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from sesame.utils import get_token, get_user

from eures_beta.logging import RedactAccessLinks
from eures_beta.users.invitations import (
    create_invitation,
    invitation_token,
    invitation_message,
)
from eures_beta.users.models import EmployerInvitation, User
from eures_beta.users.permissions import EMPLOYER_INVITER_GROUP


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    LOGIN_EMAIL_ENABLED=False,
    DJANGO_ENVIRONMENT='production',
    EMAIL_DELIVERY_ENABLED=True,
    LOGIN_EMAIL_ORIGIN='https://testserver',
    EMAIL_HOST='smtp.example.invalid',
    DEFAULT_FROM_EMAIL='sender@example.invalid',
)
class InvitationTests(TestCase):
    def setUp(self):
        self.adviser = User.objects.create_user(
            email='adviser@example.invalid', kind='adviser'
        )
        self.employer = User.objects.create_user(
            email='existing@example.invalid', kind='employer'
        )
        call_command('sync_group_and_perms', stdout=StringIO())
        self.client.force_login(self.adviser)

    def create(self, email='new@example.invalid', language='en'):
        return create_invitation(self.adviser, email, language)

    def open_link(self, client, invitation, token=None):
        return client.get(
            reverse('employer_invitation_confirm'),
            {'invitation': token or invitation_token(invitation)},
            follow=True,
        )

    def test_dashboard_lists_employers_only_and_employer_keeps_placeholder(self):
        invitation = self.create()
        page = self.client.get(reverse('dashboard'), {'lang': 'en'})
        self.assertContains(page, self.employer.email)
        self.assertContains(page, invitation.email)
        self.assertContains(page, 'Invite an employer')
        self.assertContains(page, 'Invitation pending')
        self.assertEqual(list(page.context['employers']), [self.employer])
        self.client.force_login(self.employer)
        page = self.client.get(reverse('dashboard'), {'lang': 'en'})
        self.assertContains(page, 'Your offers')
        self.assertNotContains(page, invitation.email)
        self.assertNotContains(page, 'Invite an employer')

    def test_anonymous_employer_inactive_and_revoked_adviser_cannot_invite(self):
        clients = [Client()]
        for user in (
            self.employer,
            User.objects.create_user(
                email='inactive@example.invalid', kind='adviser', is_active=False
            ),
        ):
            client = Client()
            client.force_login(user)
            clients.append(client)
        self.adviser.groups.clear()
        clients.append(self.client)
        for client in clients:
            for method in ('get', 'post'):
                response = getattr(client, method)(
                    reverse('employer_invite'),
                    {'email': 'blocked@example.invalid', 'language': 'en'},
                )
                self.assertIn(response.status_code, (302, 403))
        self.assertFalse(EmployerInvitation.objects.exists())

    def test_disabled_delivery_saves_invitation_without_user_email_or_public_link(self):
        count = User.objects.count()
        page = self.client.post(
            reverse('employer_invite') + '?lang=en',
            {
                'email': 'NEW@example.invalid',
                'language': 'de',
                'kind': 'adviser',
                'is_staff': 'on',
            },
        )
        self.assertContains(page, 'No email has been sent')
        invitation = EmployerInvitation.objects.get()
        self.assertEqual(invitation.email, 'new@example.invalid')
        self.assertEqual(invitation.invited_by, self.adviser)
        self.assertEqual(invitation.language, 'de')
        self.assertAlmostEqual(
            (invitation.expires_at - invitation.created_at).total_seconds(),
            7 * 86400,
            delta=2,
        )
        self.assertEqual(User.objects.count(), count)
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotContains(page, '?invitation=')
        self.assertIsNone(invitation.email_sent_at)

    def test_configured_backend_simulates_real_email_and_never_exposes_token_in_ui(
        self,
    ):
        with override_settings(LOGIN_EMAIL_ENABLED=True):
            page = self.client.post(
                reverse('employer_invite'),
                {'email': 'mail@example.invalid', 'language': 'en'},
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mail@example.invalid'])
        self.assertIn('valid for seven days', mail.outbox[0].body)
        self.assertIn(
            'https://testserver/accounts/invitations/confirm/?invitation=',
            mail.outbox[0].body,
        )
        self.assertNotContains(page, '?invitation=')
        self.assertIsNotNone(EmployerInvitation.objects.get().email_sent_at)

    def test_manual_email_command_is_explicit_and_validates_origin(self):
        invitation = self.create()
        output = StringIO()
        call_command(
            'invitation_email',
            str(invitation.pk),
            origin='https://testserver',
            stdout=output,
        )
        self.assertIn('Your invitation to Match Europe', output.getvalue())
        self.assertIn('?invitation=', output.getvalue())
        self.assertIsNone(EmployerInvitation.objects.get().email_sent_at)
        for origin in (
            'https://attacker.invalid',
            'https://testserver@attacker.invalid',
            'https://testserver/path',
            'http://testserver',
        ):
            with self.assertRaises(ValidationError):
                invitation_message(invitation, origin)

    def test_manual_login_email_uses_one_hour_and_never_creates_an_account(self):
        output = StringIO()
        call_command(
            'login_email',
            self.adviser.email,
            origin='https://testserver',
            language='en',
            stdout=output,
        )
        self.assertIn('expires after one hour', output.getvalue())
        self.assertIn('?sesame=', output.getvalue())
        with self.assertRaises(CommandError):
            call_command(
                'login_email',
                'unknown@example.invalid',
                origin='https://testserver',
                stdout=StringIO(),
            )
        self.assertEqual(User.objects.count(), 2)

    def test_every_new_page_and_invitation_email_is_translated(self):
        for language, label, subject in (
            ('fr', 'Inviter un employeur', 'Votre invitation à Match Europe'),
            ('en', 'Invite an employer', 'Your invitation to Match Europe'),
            ('de', 'Arbeitgeber einladen', 'Ihre Einladung zu Match Europe'),
        ):
            for name in ('dashboard', 'employer_invite'):
                self.assertContains(
                    self.client.get(reverse(name), {'lang': language}), label
                )
            invitation = self.create(
                email=f'{language}@example.invalid', language=language
            )
            self.assertEqual(
                invitation_message(invitation, 'https://testserver')[0], subject
            )
            browser = Client()
            self.open_link(browser, invitation)
            self.assertContains(
                browser.get(reverse('employer_invitation_confirm')),
                f'<html lang="{language}">',
            )

    def test_invitation_is_valid_near_one_week_but_not_after(self):
        import time
        from eures_beta.users.invitations import find_invitation

        invitation = self.create()
        token = invitation_token(invitation)
        now = timezone.now()
        for delta, expected in (
            (timedelta(days=6, hours=23), True),
            (timedelta(days=7, seconds=1), False),
        ):
            with (
                patch(
                    'django.core.signing.time.time',
                    return_value=time.time() + delta.total_seconds(),
                ),
                patch(
                    'eures_beta.users.invitations.timezone.now',
                    return_value=now + delta,
                ),
            ):
                self.assertEqual(find_invitation(token) is not None, expected)

    def test_invitation_from_deactivated_adviser_is_rejected(self):
        invitation = self.create()
        browser = Client()
        self.open_link(browser, invitation)
        User.objects.filter(pk=self.adviser.pk).update(is_active=False)
        self.assertEqual(
            browser.post(reverse('employer_invitation_confirm')).context['stage'],
            'invalid',
        )
        self.assertFalse(User.objects.filter(email=invitation.email).exists())

    def test_get_does_not_create_account_and_confirmation_creates_only_employer(self):
        invitation = self.create()
        browser = Client()
        page = self.open_link(browser, invitation)
        self.assertContains(page, 'Accept invitation and sign in')
        self.assertNotContains(page, '?invitation=')
        self.assertEqual(page['Referrer-Policy'], 'same-origin')
        self.assertFalse(User.objects.filter(email=invitation.email).exists())
        response = browser.post(
            reverse('employer_invitation_confirm'),
            {'kind': 'adviser', 'is_staff': 'on'},
            follow=True,
        )
        self.assertContains(response, 'Your offers')
        user = User.objects.get(email=invitation.email)
        self.assertEqual(user.kind, 'employer')
        self.assertTrue(user.is_active)
        self.assertFalse(
            user.is_staff or user.is_superuser or user.has_usable_password()
        )
        self.assertFalse(user.groups.exists())
        self.assertEqual(browser.session['_auth_user_id'], str(user.pk))
        self.assertEqual(browser.session.get_expiry_age(), 30 * 86400)
        invitation.refresh_from_db()
        self.assertEqual(invitation.employer, user)
        self.assertIsNotNone(invitation.accepted_at)
        self.assertFalse(
            EmployerInvitation.objects.filter(accepted_at__isnull=True).exists()
        )

    def test_two_browsers_cannot_use_same_invitation_twice(self):
        invitation = self.create()
        first, second = Client(), Client()
        self.open_link(first, invitation)
        self.open_link(second, invitation)
        first.post(reverse('employer_invitation_confirm'))
        page = second.post(reverse('employer_invitation_confirm'))
        self.assertEqual(page.context['stage'], 'invalid')
        self.assertNotIn('_auth_user_id', second.session)
        self.assertEqual(User.objects.filter(email=invitation.email).count(), 1)

    def test_expired_tampered_and_missing_links_never_create_accounts(self):
        invitation = self.create()
        old_token = invitation_token(invitation)
        for token in ('bad', old_token + 'tampered', 'x' * 513):
            browser = Client()
            self.open_link(browser, invitation, token)
            self.assertEqual(
                browser.post(reverse('employer_invitation_confirm')).context['stage'],
                'invalid',
            )
        browser = Client()
        self.open_link(browser, invitation)
        EmployerInvitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            browser.post(reverse('employer_invitation_confirm')).context['stage'],
            'invalid',
        )
        self.assertFalse(User.objects.filter(email=invitation.email).exists())

    def test_expired_invitation_renewal_revokes_old_link(self):
        invitation = self.create()
        token = invitation_token(invitation)
        EmployerInvitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        renewed = self.create()
        self.assertEqual(invitation.pk, renewed.pk)
        browser = Client()
        self.open_link(browser, renewed, token)
        self.assertEqual(
            browser.post(reverse('employer_invitation_confirm')).context['stage'],
            'invalid',
        )
        self.open_link(browser, renewed)
        self.assertEqual(
            browser.post(reverse('employer_invitation_confirm')).status_code, 302
        )

    def test_existing_account_or_pending_invitation_is_not_duplicated(self):
        self.create()
        for email in (
            'EXISTING@example.invalid',
            'ADVISER@example.invalid',
            'NEW@example.invalid',
        ):
            response = self.client.post(
                reverse('employer_invite'), {'email': email, 'language': 'en'}
            )
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(EmployerInvitation.objects.count(), 1)

    def test_account_created_elsewhere_is_not_promoted_or_modified(self):
        invitation = self.create()
        user = User.objects.create_user(email=invitation.email, kind='adviser')
        browser = Client()
        self.open_link(browser, invitation)
        self.assertEqual(
            browser.post(reverse('employer_invitation_confirm')).context['stage'],
            'invalid',
        )
        user.refresh_from_db()
        self.assertEqual(user.kind, 'adviser')
        self.assertIsNone(user.last_login)

    def test_hourly_limit_applies_to_one_adviser_across_browsers(self):
        for i in range(10):
            self.create(email=f'limited{i}@example.invalid')
        page = self.client.post(
            reverse('employer_invite'),
            {'email': 'blocked@example.invalid', 'language': 'en'},
        )
        self.assertTrue(page.context['form'].errors)
        self.assertEqual(EmployerInvitation.objects.count(), 10)

    def test_permissions_are_versioned_and_new_advisers_get_only_invitation_rights(
        self,
    ):
        user = User.objects.create_user(
            email='new-adviser@example.invalid', kind='adviser'
        )
        self.assertTrue(user.has_perm('users.add_employerinvitation'))
        self.assertFalse(user.has_perm('users.add_user'))
        self.assertFalse(user.is_staff)
        user.groups.clear()
        call_command('sync_group_and_perms', stdout=StringIO())
        self.assertTrue(
            User.objects.get(pk=user.pk).has_perm('users.view_employerinvitation')
        )
        self.assertEqual(
            set(
                Group.objects.get(name=EMPLOYER_INVITER_GROUP).permissions.values_list(
                    'codename', flat=True
                )
            ),
            {'add_employerinvitation', 'view_employerinvitation'},
        )

    def test_https_csrf_required_for_inviting_and_accepting(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.adviser)
        self.assertEqual(
            client.post(
                reverse('employer_invite'),
                {'email': 'csrf@example.invalid', 'language': 'en'},
                secure=True,
            ).status_code,
            403,
        )
        invitation = self.create()
        client = Client(enforce_csrf_checks=True)
        page = client.get(
            reverse('employer_invitation_confirm'),
            {'invitation': invitation_token(invitation)},
            secure=True,
        )
        self.assertEqual(page['Referrer-Policy'], 'no-referrer')
        client.get(page.url, secure=True)
        self.assertEqual(client.post(page.url, secure=True).status_code, 403)
        response = client.post(
            page.url,
            {'csrfmiddlewaretoken': client.cookies['csrftoken'].value},
            secure=True,
            HTTP_ORIGIN='https://testserver',
            HTTP_REFERER='https://testserver/accounts/invitations/confirm/',
        )
        self.assertEqual(response.status_code, 302)

    def test_delivery_failure_is_explicit_and_logs_no_personal_data(self):
        with (
            override_settings(LOGIN_EMAIL_ENABLED=True),
            patch(
                'eures_beta.users.invitation_views.send_mail',
                side_effect=RuntimeError('sensitive payload'),
            ),
        ):
            with self.assertLogs(
                'eures_beta.users.invitation_views', level='ERROR'
            ) as captured:
                page = self.client.post(
                    reverse('employer_invite') + '?lang=en',
                    {'email': 'secret@example.invalid', 'language': 'en'},
                )
        self.assertContains(page, 'No email has been sent')
        self.assertNotIn('secret@example.invalid', str(captured.output))
        self.assertNotIn('sensitive payload', str(captured.output))

    def test_link_durations_are_one_hour_and_one_week(self):
        self.assertEqual(settings.SESAME_MAX_AGE, 3600)
        self.assertEqual(settings.EMPLOYER_INVITATION_MAX_AGE, 7 * 86400)
        token = get_token(self.adviser)
        import time

        with patch('sesame.tokens_v2.time.time', return_value=time.time() + 1800):
            self.assertIsNotNone(get_user(token, update_last_login=False))
        with patch('sesame.tokens_v2.time.time', return_value=time.time() + 3601):
            self.assertIsNone(get_user(token, update_last_login=False))

    def test_access_log_redacts_invitation_links(self):
        record = logging.LogRecord(
            'django.server',
            logging.INFO,
            '',
            0,
            'GET /accounts/invitations/confirm/?invitation=secret',
            (),
            None,
        )
        RedactAccessLinks().filter(record)
        self.assertNotIn('secret', record.getMessage())
